
from pathlib import Path
import json

import joblib
import numpy as np
import pandas as pd

from sklearn.metrics import (
    precision_recall_curve,
    classification_report,
    confusion_matrix,
    f1_score
)

BASE_DIR = Path(__file__).resolve().parents[1]

MODEL_PATH = BASE_DIR / "models" / "salamasphere_swahili_baseline.joblib"
DATA_DIR = BASE_DIR / "Data" / "processed"
REPORT_DIR = BASE_DIR / "reports"

TARGET_RECALL = 0.70

print("=" * 60)
print("SALAMASPHERE - DECISION THRESHOLD EXPERIMENT")
print("=" * 60)

model = joblib.load(MODEL_PATH)

validation = pd.read_csv(DATA_DIR / "validation.csv")
test = pd.read_csv(DATA_DIR / "test.csv")

def prepare(df):
    df = df.dropna(subset=["text", "labels"]).copy()
    return (
        df["text"].astype(str),
        df["labels"].astype(int)
    )

X_val, y_val = prepare(validation)
X_test, y_test = prepare(test)

# Validation probabilities
val_probabilities = model.predict_proba(X_val)[:, 1]

precision, recall, thresholds = precision_recall_curve(
    y_val, val_probabilities
)

# Find best F1 threshold on validation data
f1_values = (
    2 * precision[:-1] * recall[:-1]
    / (precision[:-1] + recall[:-1] + 1e-12)
)

best_f1_index = int(np.argmax(f1_values))
best_f1_threshold = float(thresholds[best_f1_index])

# Find the highest precision threshold that achieves
# the requested minimum validation recall.
eligible = np.where(recall[:-1] >= TARGET_RECALL)[0]

if len(eligible):
    target_index = eligible[
        np.argmax(precision[eligible])
    ]
    selected_threshold = float(thresholds[target_index])
    selection_reason = (
        f"Highest validation precision with recall >= "
        f"{TARGET_RECALL:.0%}"
    )
else:
    selected_threshold = best_f1_threshold
    selection_reason = (
        "70% validation recall was not achievable; "
        "using best validation F1 threshold instead."
    )

print("\nTHRESHOLD SELECTION")
print("Default threshold: 0.50")
print("Best validation F1 threshold:", best_f1_threshold)
print("Selected threshold:", selected_threshold)
print("Selection reason:", selection_reason)

def show_results(name, y_true, probabilities, threshold):
    predictions = (probabilities >= threshold).astype(int)

    print(f"\n{name} - THRESHOLD {threshold:.4f}")
    print(classification_report(
        y_true,
        predictions,
        target_names=["Non-offensive", "Offensive"],
        zero_division=0
    ))

    print("Confusion matrix:")
    print(confusion_matrix(y_true, predictions))

    return predictions

# Compare current and tuned validation results
show_results(
    "VALIDATION DEFAULT",
    y_val,
    val_probabilities,
    0.50
)

show_results(
    "VALIDATION TUNED",
    y_val,
    val_probabilities,
    selected_threshold
)

# Evaluate the selected threshold ONCE on the test set.
test_probabilities = model.predict_proba(X_test)[:, 1]

test_predictions = show_results(
    "FINAL TEST AT VALIDATION-SELECTED THRESHOLD",
    y_test,
    test_probabilities,
    selected_threshold
)

# Save threshold and final evaluation
metrics = {
    "model": "TF-IDF + Logistic Regression",
    "selected_threshold": selected_threshold,
    "selection_reason": selection_reason,
    "test_f1_macro": float(
        f1_score(y_test, test_predictions, average="macro")
    ),
    "test_confusion_matrix": confusion_matrix(
        y_test, test_predictions
    ).tolist()
}

REPORT_DIR.mkdir(parents=True, exist_ok=True)

with open(
    REPORT_DIR / "threshold_experiment.json",
    "w",
    encoding="utf-8"
) as file:
    json.dump(metrics, file, indent=4)

print("\nSaved threshold experiment report.")
print(json.dumps(metrics, indent=4))
print("\nEXPERIMENT COMPLETED")
