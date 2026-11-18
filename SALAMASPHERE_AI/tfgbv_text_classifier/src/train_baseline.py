
from pathlib import Path
import json

import joblib
import pandas as pd

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    classification_report,
)

BASE_DIR = Path(__file__).resolve().parents[1]

DATA_DIR = BASE_DIR / "Data" / "processed"
MODEL_DIR = BASE_DIR / "models"
REPORT_DIR = BASE_DIR / "reports"

MODEL_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)

def load_split(name):
    path = DATA_DIR / f"{name}.csv"

    if not path.exists():
        raise FileNotFoundError(f"Missing dataset: {path}")

    df = pd.read_csv(path)

    required = {"text", "labels"}

    if not required.issubset(df.columns):
        raise ValueError(
            f"{path} must contain columns {required}"
        )

    df = df.dropna(subset=["text", "labels"])
    df["text"] = df["text"].astype(str)
    df["labels"] = df["labels"].astype(int)

    if not set(df["labels"].unique()).issubset({0, 1}):
        raise ValueError("Unexpected labels found.")

    return df

print("=" * 60)
print("SALAMASPHERE KISWAHILI OFFENSIVE LANGUAGE BASELINE")
print("=" * 60)

train_df = load_split("train")
val_df = load_split("validation")

X_train = train_df["text"]
y_train = train_df["labels"]

X_val = val_df["text"]
y_val = val_df["labels"]


print("\nDataset sizes:")
print("Training:", len(train_df))
print("Validation:", len(val_df))
print("Testing: not loaded by the training script")

# Combine word and character features.
features = FeatureUnion([
    (
        "word",
        TfidfVectorizer(
            analyzer="word",
            ngram_range=(1, 2),
            min_df=2,
            max_features=50000,
            sublinear_tf=True
        )
    ),
    (
        "character",
        TfidfVectorizer(
            analyzer="char",
            ngram_range=(2, 5),
            min_df=2,
            max_features=50000,
            sublinear_tf=True
        )
    )
])

model = Pipeline([
    ("features", features),
    (
        "classifier",
        LogisticRegression(
            max_iter=1000,
            class_weight="balanced",
            random_state=42
        )
    )
])

print("\nTraining model...")

model.fit(X_train, y_train)

print("Training completed.")

# Validation evaluation
val_predictions = model.predict(X_val)

print("\nVALIDATION RESULTS")
print(classification_report(
    y_val,
    val_predictions,
    target_names=["Non-offensive", "Offensive"],
    zero_division=0
))

metrics = {
    "model": "TF-IDF + Logistic Regression",
    "dataset": "metabloit/offensive-swahili-text",
    "train_examples": len(train_df),
    "validation_examples": len(val_df),
    "evaluation_split": "validation",
    "validation_classification_report": classification_report(
        y_val, val_predictions,
        target_names=["Non-offensive", "Offensive"],
        zero_division=0,
        output_dict=True,
    ),
}

model_path = MODEL_DIR / "salamasphere_swahili_baseline.joblib"

joblib.dump(model, model_path)

report_path = REPORT_DIR / "baseline_metrics.json"

with open(report_path, "w", encoding="utf-8") as f:
    json.dump(metrics, f, indent=4)

print("\nSaved model:", model_path)
print("Saved metrics:", report_path)

print("\nVALIDATION METRICS")
print(json.dumps(metrics, indent=4))

print("\nBASELINE TRAINING COMPLETED")
