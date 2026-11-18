"""Select and report a logistic-regression threshold on validation data only."""

from pathlib import Path
import json

import joblib
import numpy as np
import pandas as pd

from sklearn.metrics import classification_report, precision_recall_curve


BASE_DIR = Path(__file__).resolve().parents[1]
MODEL_PATH = BASE_DIR / "models" / "salamasphere_swahili_baseline.joblib"
VALIDATION_PATH = BASE_DIR / "Data" / "processed" / "validation.csv"
REPORT_PATH = BASE_DIR / "reports" / "threshold_experiment.json"
TARGET_RECALL = 0.70


def main() -> None:
    model = joblib.load(MODEL_PATH)
    frame = pd.read_csv(VALIDATION_PATH).dropna(subset=["text", "labels"])
    texts = frame["text"].astype(str)
    labels = frame["labels"].astype(int)
    scores = model.predict_proba(texts)[:, 1]
    precision, recall, thresholds = precision_recall_curve(labels, scores)
    f1 = 2 * precision[:-1] * recall[:-1] / (
        precision[:-1] + recall[:-1] + 1e-12
    )
    best_f1_index = int(np.argmax(f1))
    eligible = np.where(recall[:-1] >= TARGET_RECALL)[0]

    if len(eligible):
        selected_index = int(eligible[np.argmax(precision[eligible])])
        reason = f"Highest validation precision with recall >= {TARGET_RECALL:.0%}"
    else:
        selected_index = best_f1_index
        reason = "Target validation recall unavailable; selected best validation F1"

    threshold = float(thresholds[selected_index])
    predictions = (scores >= threshold).astype(int)
    result = {
        "model": "TF-IDF + Logistic Regression",
        "selected_threshold": threshold,
        "selection_reason": reason,
        "evaluation_split": "validation",
        "validation_examples": int(len(frame)),
        "validation_classification_report": classification_report(
            labels, predictions,
            target_names=["Non-offensive", "Offensive"],
            output_dict=True,
            zero_division=0,
        ),
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"Validation threshold: {threshold:.6f}")
    print("Saved validation-only threshold report.")


if __name__ == "__main__":
    main()
