"""Run the one final test evaluation for the already validation-selected model."""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "reports" / "selected_model.json"
OUTPUT_JSON = ROOT / "reports" / "final_model_evaluation.json"
OUTPUT_MD = ROOT / "reports" / "final_model_evaluation.md"


def main() -> None:
    if OUTPUT_JSON.exists() or OUTPUT_MD.exists():
        raise FileExistsError(
            "Final evaluation report already exists; refusing to rerun the held-out test evaluation."
        )
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    artifact = (ROOT / config["artifact"]).resolve()
    model = joblib.load(artifact)
    frame = pd.read_csv(ROOT / "Data" / "processed" / "test.csv").dropna(subset=["text", "labels"])
    x_test = frame["text"].astype(str)
    y_test = frame["labels"].astype(int)
    scores = model.decision_function(x_test)
    predictions = (scores >= float(config["threshold"])).astype(int)
    matrix = confusion_matrix(y_test, predictions, labels=[0, 1])
    report = classification_report(
        y_test, predictions, labels=[0, 1],
        target_names=["non_offensive", "offensive"],
        output_dict=True, zero_division=0,
    )
    result = {
        "evaluation_status": "completed_once_after_validation_selection",
        "model_name": config["model_name"],
        "model_version": config["model_version"],
        "artifact": config["artifact"],
        "test_examples": int(len(frame)),
        "threshold": float(config["threshold"]),
        "score_type": config["score_type"],
        "accuracy": float(accuracy_score(y_test, predictions)),
        "macro_f1": float(f1_score(y_test, predictions, average="macro", zero_division=0)),
        "offensive_precision": float(precision_score(y_test, predictions, pos_label=1, zero_division=0)),
        "offensive_recall": float(recall_score(y_test, predictions, pos_label=1, zero_division=0)),
        "false_negative_rate": float(matrix[1, 0] / max(1, int((y_test == 1).sum()))),
        "false_positive_rate": float(matrix[0, 1] / max(1, int((y_test == 0).sum()))),
        "confusion_matrix_labels_0_1": matrix.tolist(),
        "per_class": {
            "non_offensive": report["non_offensive"],
            "offensive": report["offensive"],
        },
        "test_independence_warning": (
            "This test split was previously used for evaluation/error analysis of earlier model artifacts. "
            "These results are a single final descriptive evaluation, not an untouched independent estimate. "
            "Do not tune from these results."
        ),
        "tfgbv_limitation": "General offensive-language baseline; not validated as a TFGBV detector.",
    }
    OUTPUT_JSON.write_text(json.dumps(result, indent=2), encoding="utf-8")
    markdown = f"""# Final model evaluation

**Model:** {result['model_name']} (`{result['model_version']}`)  
**Test examples:** {result['test_examples']}  
**Score threshold:** {result['threshold']:.6f} LinearSVC decision margin (not a probability)

| Metric | Result |
|---|---:|
| Accuracy | {result['accuracy']:.4f} |
| Macro F1 | {result['macro_f1']:.4f} |
| Offensive precision | {result['offensive_precision']:.4f} |
| Offensive recall | {result['offensive_recall']:.4f} |
| Offensive false-negative rate | {result['false_negative_rate']:.4f} |
| Non-offensive false-positive rate | {result['false_positive_rate']:.4f} |

Confusion matrix (actual rows, predicted columns; labels 0, 1): `{matrix.tolist()}`.

## Evaluation limitation

{result['test_independence_warning']}

This is a general offensive-language baseline, not a validated TFGBV detection system. The score is a decision margin, not a calibrated probability or real-world risk estimate. See `data_and_error_analysis.md` for dataset and historical result context.
"""
    OUTPUT_MD.write_text(markdown, encoding="utf-8")
    print("Final test evaluation completed once; message text was not printed.")
    print(f"Examples: {len(frame)} | macro F1: {result['macro_f1']:.4f}")
    print(f"Offensive precision: {result['offensive_precision']:.4f} | recall: {result['offensive_recall']:.4f}")
    print("Confusion matrix (labels 0,1):", matrix.tolist())
    print("Reports:", OUTPUT_JSON, OUTPUT_MD)
    print("Warning: prior test exposure means this is not an untouched independent estimate.")


if __name__ == "__main__":
    main()
