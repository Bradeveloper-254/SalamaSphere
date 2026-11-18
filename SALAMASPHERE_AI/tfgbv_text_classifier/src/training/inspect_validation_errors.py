
from pathlib import Path
import json
import joblib
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]

DATA_DIR = BASE_DIR / "Data" / "processed"
MODEL_DIR = BASE_DIR / "models"
REPORT_DIR = BASE_DIR / "reports"

MODEL_PATH = MODEL_DIR / "salamasphere_swahili_baseline.joblib"
THRESHOLD_PATH = REPORT_DIR / "threshold_experiment.json"
VALIDATION_PATH = DATA_DIR / "validation.csv"

OUTPUT_PATH = REPORT_DIR / "validation_misclassified.csv"

# Load validation data
df = pd.read_csv(VALIDATION_PATH)
df = df.dropna(subset=["text", "labels"]).copy()

# Load selected threshold
with open(THRESHOLD_PATH, encoding="utf-8") as file:
    threshold_data = json.load(file)

threshold = threshold_data["selected_threshold"]

# Load trained model
model = joblib.load(MODEL_PATH)

# Generate predictions
texts = df["text"].astype(str)
df["actual"] = df["labels"].astype(int)
df["offensive_probability"] = model.predict_proba(texts)[:, 1]
df["predicted"] = (
    df["offensive_probability"] >= threshold
).astype(int)

# Identify incorrect predictions
errors = df[df["actual"] != df["predicted"]].copy()

errors["error_type"] = errors.apply(
    lambda row: (
        "false_negative"
        if row["actual"] == 1 and row["predicted"] == 0
        else "false_positive"
    ),
    axis=1
)

# Sort errors by confidence
errors = errors.sort_values(
    by="offensive_probability",
    ascending=True
)

# Save locally for manual inspection
errors[
    [
        "text",
        "actual",
        "predicted",
        "offensive_probability",
        "error_type"
    ]
].to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")

print("=" * 55)
print("VALIDATION ERROR INSPECTION")
print("=" * 55)

print(f"\nValidation examples: {len(df)}")
print(f"Incorrect predictions: {len(errors)}")

print("\nError counts:")
print(errors["error_type"].value_counts())

print("\nFalse negatives:")
print(
    errors[errors["error_type"] == "false_negative"][
        ["actual", "predicted", "offensive_probability"]
    ].head(10).to_string(index=False)
)

print("\nFalse positives:")
print(
    errors[errors["error_type"] == "false_positive"][
        ["actual", "predicted", "offensive_probability"]
    ].head(10).to_string(index=False)
)

print(f"\nDetailed errors saved to:\n{OUTPUT_PATH}")
print("\nVALIDATION ERROR INSPECTION COMPLETED")
