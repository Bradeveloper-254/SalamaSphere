"""Compare a small set of baselines using train fitting and validation selection only."""

from __future__ import annotations

import json
import unicodedata
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
)
from sklearn.naive_bayes import ComplementNB
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "Data" / "processed"
MODELS_DIR = ROOT / "models"
EXPERIMENT_MODELS_DIR = MODELS_DIR / "experiments"
REPORT_PATH = ROOT / "reports" / "validation_model_comparison.json"
MIN_OFFENSIVE_RECALL = 0.70
SEED = 42


def load_split(name: str) -> tuple[pd.Series, pd.Series]:
    frame = pd.read_csv(DATA_DIR / f"{name}.csv")
    frame = frame.dropna(subset=["text", "labels"])
    texts = frame["text"].astype(str)
    labels = frame["labels"].astype(int)
    return texts, labels


def normalize_text(text: str) -> str:
    """Conservative Unicode/whitespace cleanup; preserve punctuation and tokens."""
    return " ".join(unicodedata.normalize("NFKC", text).split())


def select_threshold(y_true: pd.Series, scores: np.ndarray) -> tuple[float, str]:
    precision, recall, thresholds = precision_recall_curve(y_true, scores)
    eligible = np.flatnonzero(recall[:-1] >= MIN_OFFENSIVE_RECALL)
    if len(eligible):
        chosen = int(eligible[np.argmax(precision[eligible])])
        return float(thresholds[chosen]), f"Highest validation precision with offensive recall >= {MIN_OFFENSIVE_RECALL:.0%}"
    f1 = 2 * precision[:-1] * recall[:-1] / (precision[:-1] + recall[:-1] + 1e-12)
    chosen = int(np.argmax(f1))
    return float(thresholds[chosen]), "Recall target unavailable; best validation offensive F1"


def feature_union(*, char_analyzer: str = "char", char_range: tuple[int, int] = (2, 5)) -> FeatureUnion:
    return FeatureUnion([
        ("word", TfidfVectorizer(
            analyzer="word", ngram_range=(1, 2), min_df=2,
            max_features=50_000, sublinear_tf=True,
        )),
        ("character", TfidfVectorizer(
            analyzer=char_analyzer, ngram_range=char_range, min_df=2,
            max_features=50_000, sublinear_tf=True,
        )),
    ])


def score_candidate(
    name: str,
    model: Any,
    y_true: pd.Series,
    scores: np.ndarray,
    *,
    score_kind: str,
    config: dict[str, Any],
) -> dict[str, Any]:
    threshold, reason = select_threshold(y_true, scores)
    predicted = (scores >= threshold).astype(int)
    report = classification_report(
        y_true, predicted, labels=[0, 1],
        target_names=["non_offensive", "offensive"],
        output_dict=True, zero_division=0,
    )
    result: dict[str, Any] = {
        "name": name,
        "score_kind": score_kind,
        "threshold": threshold,
        "threshold_selection": reason,
        "validation_examples": int(len(y_true)),
        "accuracy": float(accuracy_score(y_true, predicted)),
        "macro_f1": float(f1_score(y_true, predicted, average="macro", zero_division=0)),
        "offensive_precision": float(precision_score(y_true, predicted, pos_label=1, zero_division=0)),
        "offensive_recall": float(recall_score(y_true, predicted, pos_label=1, zero_division=0)),
        "false_negative_rate": float(confusion_matrix(y_true, predicted, labels=[0, 1])[1, 0] / max(1, int((y_true == 1).sum()))),
        "false_positive_rate": float(confusion_matrix(y_true, predicted, labels=[0, 1])[0, 1] / max(1, int((y_true == 0).sum()))),
        "confusion_matrix_labels_0_1": confusion_matrix(y_true, predicted, labels=[0, 1]).tolist(),
        "per_class": {
            "non_offensive": report["non_offensive"],
            "offensive": report["offensive"],
        },
        "config": config,
    }
    if score_kind == "probability":
        # This is a validation-set diagnostic, not a claim of deployment calibration.
        labels = y_true.to_numpy()
        result["brier_score_validation"] = float(np.mean((scores - labels) ** 2))
        bins = np.linspace(0.0, 1.0, 11)
        calibration_bins = []
        ece = 0.0
        for index in range(len(bins) - 1):
            included = (scores >= bins[index]) & (
                scores <= bins[index + 1] if index == len(bins) - 2 else scores < bins[index + 1]
            )
            count = int(included.sum())
            if not count:
                continue
            mean_score = float(scores[included].mean())
            observed_rate = float(labels[included].mean())
            ece += count / len(labels) * abs(mean_score - observed_rate)
            calibration_bins.append({
                "lower": float(bins[index]), "upper": float(bins[index + 1]),
                "count": count, "mean_score": mean_score,
                "observed_offensive_rate": observed_rate,
            })
        result["expected_calibration_error_10_bins_validation"] = float(ece)
        result["calibration_bins_validation"] = calibration_bins
    return result


def main() -> None:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    EXPERIMENT_MODELS_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    x_train, y_train = load_split("train")
    x_val, y_val = load_split("validation")
    results: list[dict[str, Any]] = []

    # Refit comparable candidates on the latest cleaned train split. Existing
    # published artifacts remain untouched in models/.
    baseline = Pipeline([
        ("features", feature_union()),
        ("classifier", LogisticRegression(
            max_iter=1000, class_weight="balanced", random_state=SEED,
        )),
    ])
    baseline.fit(x_train, y_train)
    baseline_path = EXPERIMENT_MODELS_DIR / "clean_word_char_logistic.joblib"
    joblib.dump(baseline, baseline_path)
    baseline_probability = baseline.predict_proba(x_val)[:, 1]
    results.append(score_candidate(
        "clean_word_char_logistic", baseline, y_val, baseline_probability,
        score_kind="probability", config={
            "word_ngrams": [1, 2], "character_analyzer": "char",
            "character_ngrams": [2, 5], "random_state": SEED,
            "artifact": str(baseline_path.relative_to(ROOT)),
        },
    ))

    svm_model = Pipeline([
        ("features", feature_union()),
        ("classifier", LinearSVC(
            C=1.0, class_weight="balanced", max_iter=5000, random_state=SEED,
        )),
    ])
    svm_model.fit(x_train, y_train)
    svm_path = EXPERIMENT_MODELS_DIR / "clean_word_char_linear_svm.joblib"
    joblib.dump(svm_model, svm_path)
    svm_scores = svm_model.decision_function(x_val)
    results.append(score_candidate(
        "clean_word_char_linear_svm", svm_model, y_val, svm_scores,
        score_kind="decision_score", config={
            "word_ngrams": [1, 2], "character_analyzer": "char",
            "character_ngrams": [2, 5], "C": 1.0,
            "random_state": SEED,
            "artifact": str(svm_path.relative_to(ROOT)),
        },
    ))

    # Controlled preprocessing experiment: identical features, only normalize
    # Unicode and whitespace. Punctuation, negation, and repeated characters stay.
    normalized_logistic = Pipeline([
        ("features", feature_union()),
        ("classifier", LogisticRegression(
            max_iter=1500, class_weight="balanced", random_state=SEED,
        )),
    ])
    x_train_normalized = x_train.map(normalize_text)
    x_val_normalized = x_val.map(normalize_text)
    normalized_logistic.fit(x_train_normalized, y_train)
    normalized_probability = normalized_logistic.predict_proba(x_val_normalized)[:, 1]
    normalized_path = EXPERIMENT_MODELS_DIR / "unicode_whitespace_logistic.joblib"
    joblib.dump(normalized_logistic, normalized_path)
    results.append(score_candidate(
        "unicode_whitespace_word_char_logistic", normalized_logistic, y_val,
        normalized_probability, score_kind="probability",
        config={
            "normalization": "NFKC and whitespace collapse; punctuation and tokens preserved",
            "word_ngrams": [1, 2], "character_analyzer": "char",
            "character_ngrams": [2, 5], "random_state": SEED,
            "artifact": str(normalized_path.relative_to(ROOT)),
        },
    ))

    charwb_logistic = Pipeline([
        ("features", feature_union(char_analyzer="char_wb", char_range=(3, 6))),
        ("classifier", LogisticRegression(
            max_iter=1500, class_weight="balanced", random_state=SEED,
        )),
    ])
    charwb_logistic.fit(x_train, y_train)
    charwb_probability = charwb_logistic.predict_proba(x_val)[:, 1]
    charwb_path = EXPERIMENT_MODELS_DIR / "charwb_word_char_logistic.joblib"
    joblib.dump(charwb_logistic, charwb_path)
    results.append(score_candidate(
        "charwb_word_char_logistic", charwb_logistic, y_val,
        charwb_probability, score_kind="probability",
        config={
            "normalization": "none beyond TfidfVectorizer defaults",
            "word_ngrams": [1, 2], "character_analyzer": "char_wb",
            "character_ngrams": [3, 6], "random_state": SEED,
            "artifact": str(charwb_path.relative_to(ROOT)),
        },
    ))

    complement_nb = Pipeline([
        ("features", feature_union()),
        ("classifier", ComplementNB(alpha=0.5, norm=True)),
    ])
    complement_nb.fit(x_train, y_train)
    complement_probability = complement_nb.predict_proba(x_val)[:, 1]
    complement_path = EXPERIMENT_MODELS_DIR / "word_char_complement_nb.joblib"
    joblib.dump(complement_nb, complement_path)
    results.append(score_candidate(
        "word_char_complement_nb", complement_nb, y_val,
        complement_probability, score_kind="probability",
        config={
            "word_ngrams": [1, 2], "character_ngrams": [2, 5],
            "alpha": 0.5, "norm": True,
            "artifact": str(complement_path.relative_to(ROOT)),
        },
    ))

    # Stable ordering makes ties reproducible and surfaces the validation macro-F1 leader.
    results.sort(key=lambda row: (-row["macro_f1"], -row["offensive_recall"], row["name"]))
    output = {
        "selection_split": "validation",
        "fit_split_for_new_models": "train",
        "test_split_accessed": False,
        "threshold_policy": f"maximize precision subject to offensive recall >= {MIN_OFFENSIVE_RECALL:.0%}; otherwise maximize offensive F1",
        "candidates": results,
        "validation_macro_f1_leader": results[0]["name"],
        "note": "Scores and thresholds are validation diagnostics, not TFGBV risk probabilities.",
    }
    REPORT_PATH.write_text(json.dumps(output, indent=2), encoding="utf-8")

    print("Validation-only model comparison; test split was not accessed.")
    for row in results:
        print(
            f"{row['name']}: macro_f1={row['macro_f1']:.4f}, "
            f"offensive_precision={row['offensive_precision']:.4f}, "
            f"offensive_recall={row['offensive_recall']:.4f}, "
            f"threshold={row['threshold']:.6g} ({row['score_kind']})"
        )
    print("Validation leader:", output["validation_macro_f1_leader"])
    print("Report:", REPORT_PATH)


if __name__ == "__main__":
    main()
