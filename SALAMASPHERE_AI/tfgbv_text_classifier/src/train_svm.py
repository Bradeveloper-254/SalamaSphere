
from pathlib import Path
import json

import joblib
import numpy as np
import pandas as pd

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.svm import LinearSVC
from sklearn.metrics import (
    precision_recall_curve,
    classification_report,
    confusion_matrix,
    accuracy_score,
    f1_score
)

BASE_DIR = Path(__file__).resolve().parents[1]

DATA_DIR = BASE_DIR / "Data" / "processed"
MODEL_DIR = BASE_DIR / "models"
REPORT_DIR = BASE_DIR / "reports"

MODEL_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)

def load_data(name):
    df = pd.read_csv(DATA_DIR / f"{name}.csv")
    df = df.dropna(subset=["text", "labels"])

    return (
        df["text"].astype(str),
        df["labels"].astype(int)
    )

print("=" * 60)
print("SALAMASPHERE - LINEAR SVM EXPERIMENT")
print("=" * 60)

X_train, y_train = load_data("train")
X_val, y_val = load_data("validation")
X_test, y_test = load_data("test")

features = FeatureUnion([
    ("word", TfidfVectorizer(
        analyzer="word",
        ngram_range=(1, 2),
        min_df=2,
        max_features=50000,
        sublinear_tf=True
    )),
    ("character", TfidfVectorizer(
        analyzer="char",
        ngram_range=(2, 5),
        min_df=2,
        max_features=50000,
        sublinear_tf=True
    ))
])

model = Pipeline([
    ("features", features),
    ("classifier", LinearSVC(
        C=1.0,
        class_weight="balanced",
        max_iter=5000,
        random_state=42
    ))
])

print("\nTraining Linear SVM...")
model.fit(X_train, y_train)
print("Training completed.")

# SVM decision scores, not probabilities
val_scores = model.decision_function(X_val)

precision, recall, thresholds = precision_recall_curve(
    y_val, val_scores
)

f1_values = (
    2 * precision[:-1] * recall[:-1]
    / (precision[:-1] + recall[:-1] + 1e-12)
)

best_f1_index = int(np.argmax(f1_values))
best_f1_threshold = float(thresholds[best_f1_index])

# Select highest precision while achieving at least 70% recall
target_recall = 0.70
eligible = np.where(recall[:-1] >= target_recall)[0]

if len(eligible):
    selected_index = eligible[
        np.argmax(precision[eligible])
    ]
    threshold = float(thresholds[selected_index])
    reason = "Highest precision with validation recall >= 70%"
else:
    threshold = best_f1_threshold
    reason = "Target recall unavailable; selected best validation F1"

print("\nThreshold selected on validation data:", threshold)
print("Selection reason:", reason)

val_predictions = (val_scores >= threshold).astype(int)

print("\nVALIDATION RESULTS")
print(classification_report(
    y_val,
    val_predictions,
    target_names=["Non-offensive", "Offensive"],
    zero_division=0
))

# Evaluate on test set only after selecting the threshold
test_scores = model.decision_function(X_test)
test_predictions = (test_scores >= threshold).astype(int)

print("\nFINAL TEST RESULTS")
print(classification_report(
    y_test,
    test_predictions,
    target_names=["Non-offensive", "Offensive"],
    zero_division=0
))

metrics = {
    "model": "TF-IDF + Linear SVM",
    "threshold": threshold,
    "selection_reason": reason,
    "accuracy": float(accuracy_score(y_test, test_predictions)),
    "macro_f1": float(
        f1_score(y_test, test_predictions, average="macro")
    ),
    "confusion_matrix": confusion_matrix(
        y_test, test_predictions
    ).tolist()
}

joblib.dump(
    model,
    MODEL_DIR / "salamasphere_swahili_svm.joblib"
)

with open(
    REPORT_DIR / "svm_metrics.json",
    "w",
    encoding="utf-8"
) as f:
    json.dump(metrics, f, indent=4)

print("\nFINAL SVM METRICS")
print(json.dumps(metrics, indent=4))

print("\nSVM EXPERIMENT COMPLETED")
