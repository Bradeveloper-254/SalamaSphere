"""Inspect validation mistakes without printing message text to the console."""

from __future__ import annotations

import json
import argparse
from pathlib import Path

import joblib
import pandas as pd
from sklearn.metrics import classification_report, confusion_matrix


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "Data" / "processed" / "validation.csv"
MODEL_PATH = ROOT / "models" / "salamasphere_swahili_baseline.joblib"
THRESHOLD_PATH = ROOT / "reports" / "threshold_experiment.json"
ERRORS_PATH = ROOT / "reports" / "validation_misclassified.csv"
SUMMARY_PATH = ROOT / "reports" / "validation_error_summary.json"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, default=MODEL_PATH)
    parser.add_argument("--threshold", type=float, default=None)
    parser.add_argument("--score-kind", choices=("auto", "probability", "decision_score"), default="auto")
    parser.add_argument("--output", type=Path, default=ERRORS_PATH)
    parser.add_argument("--summary", type=Path, default=SUMMARY_PATH)
    args = parser.parse_args()
    threshold_path = THRESHOLD_PATH if args.threshold is None else None
    for path in (DATA_PATH, args.model, threshold_path):
        if path is None:
            continue
        if not path.is_file():
            raise FileNotFoundError(f"Required project artifact is missing: {path}")

    frame = pd.read_csv(DATA_PATH)
    if not {"text", "labels"}.issubset(frame.columns):
        raise ValueError("Validation CSV must contain text and labels columns.")
    frame = frame.dropna(subset=["text", "labels"]).copy()
    frame["text"] = frame["text"].astype(str)
    frame["actual"] = frame["labels"].astype(int)

    config = json.loads(THRESHOLD_PATH.read_text(encoding="utf-8")) if threshold_path else {}
    threshold = float(args.threshold if args.threshold is not None else config["selected_threshold"])

    model = joblib.load(args.model)
    score_kind = args.score_kind
    if score_kind == "auto":
        score_kind = "probability" if hasattr(model, "predict_proba") else "decision_score"
    scores = (
        model.predict_proba(frame["text"])[:, 1]
        if score_kind == "probability"
        else model.decision_function(frame["text"])
    )
    if score_kind == "probability" and not 0 <= threshold <= 1:
        raise ValueError("A probability threshold must be in [0, 1].")
    frame["predicted"] = (scores >= threshold).astype(int)
    score_column = "offensive_probability" if score_kind == "probability" else "offensive_score"
    frame[score_column] = scores
    frame["error_type"] = "correct"
    frame.loc[(frame.actual == 1) & (frame.predicted == 0), "error_type"] = "false_negative"
    frame.loc[(frame.actual == 0) & (frame.predicted == 1), "error_type"] = "false_positive"

    errors = frame.loc[frame.error_type != "correct", [
        "text", "actual", "predicted", score_column, "error_type",
    ]].copy()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    errors.to_csv(args.output, index=False, encoding="utf-8")

    y_true = frame["actual"]
    y_pred = frame["predicted"]
    summary = {
        "split": "validation",
        "threshold": threshold,
        "score_kind": score_kind,
        "model": str(args.model.relative_to(ROOT)) if args.model.is_relative_to(ROOT) else str(args.model),
        "examples": int(len(frame)),
        "errors": int(len(errors)),
        "false_negatives": int((errors.error_type == "false_negative").sum()),
        "false_positives": int((errors.error_type == "false_positive").sum()),
        "confusion_matrix_labels_0_1": confusion_matrix(y_true, y_pred, labels=[0, 1]).tolist(),
        "classification_report": classification_report(
            y_true, y_pred, labels=[0, 1], target_names=["non_offensive", "offensive"],
            output_dict=True, zero_division=0,
        ),
        "error_length_characters": {
            "median": float(errors.text.str.len().median()) if len(errors) else None,
            "mean": float(errors.text.str.len().mean()) if len(errors) else None,
        },
        "error_length_words": {
            "median": float(errors.text.str.split().str.len().median()) if len(errors) else None,
            "mean": float(errors.text.str.split().str.len().mean()) if len(errors) else None,
        },
        "artifacts": {
            "misclassified_rows": str(args.output.relative_to(ROOT)) if args.output.is_relative_to(ROOT) else str(args.output),
            "aggregate_summary": str(args.summary.relative_to(ROOT)) if args.summary.is_relative_to(ROOT) else str(args.summary),
        },
    }
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print("Validation error inspection (message contents omitted)")
    print(f"Threshold: {threshold:.6f}")
    print(f"Examples: {len(frame)} | errors: {len(errors)}")
    print(f"False negatives: {summary['false_negatives']} | false positives: {summary['false_positives']}")
    print("Confusion matrix (true rows, predicted columns; labels 0,1):")
    print(summary["confusion_matrix_labels_0_1"])
    print("Macro F1:", round(summary["classification_report"]["macro avg"]["f1-score"], 4))
    print("Misclassified messages saved locally to:", args.output)
    print("Aggregate summary saved to:", args.summary)


if __name__ == "__main__":
    main()
