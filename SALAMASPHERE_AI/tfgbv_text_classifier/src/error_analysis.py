
from pathlib import Path
import pandas as pd
import joblib
import json

from sklearn.metrics import confusion_matrix

BASE_DIR = Path(__file__).resolve().parents[1]

DATA_DIR = BASE_DIR / "Data" / "processed"
MODEL_DIR = BASE_DIR / "models"
REPORT_DIR = BASE_DIR / "reports"

MODEL_PATH = MODEL_DIR / "salamasphere_swahili_baseline.joblib"
THRESHOLD_PATH = REPORT_DIR / "threshold_experiment.json"

df = pd.read_csv(DATA_DIR / "test.csv")
df = df.dropna(subset=["text", "labels"]).copy()

with open(THRESHOLD_PATH, encoding="utf-8") as f:
    threshold_data = json.load(f)

threshold = threshold_data["selected_threshold"]

model = joblib.load(MODEL_PATH)

texts = df["text"].astype(str)
actual = df["labels"].astype(int)

probabilities = model.predict_proba(texts)[:, 1]
predicted = (probabilities >= threshold).astype(int)

df["probability_offensive"] = probabilities
df["predicted"] = predicted

df["error_type"] = "correct"

df.loc[
    (actual == 1) & (predicted == 0),
    "error_type"
] = "false_negative"

df.loc[
    (actual == 0) & (predicted == 1),
    "error_type"
] = "false_positive"

print("=" * 60)
print("SALAMASPHERE ERROR ANALYSIS")
print("=" * 60)

print("\nConfusion matrix:")
print(confusion_matrix(actual, predicted))

print("\nError distribution:")
print(df["error_type"].value_counts())

print("\nProbability distribution by actual class:")
print(
    df.groupby("labels")["probability_offensive"]
    .describe()
    .round(3)
)

# Save an aggregate report without message content.
summary = {
    "threshold": float(threshold),
    "total_test_examples": int(len(df)),
    "false_negatives": int(
        (df["error_type"] == "false_negative").sum()
    ),
    "false_positives": int(
        (df["error_type"] == "false_positive").sum()
    ),
    "correct_predictions": int(
        (df["error_type"] == "correct").sum()
    )
}

REPORT_DIR.mkdir(parents=True, exist_ok=True)

with open(
    REPORT_DIR / "error_analysis_summary.json",
    "w",
    encoding="utf-8"
) as f:
    json.dump(summary, f, indent=4)

print("\nSummary saved.")
print(json.dumps(summary, indent=4))

print("\nERROR ANALYSIS COMPLETED")
