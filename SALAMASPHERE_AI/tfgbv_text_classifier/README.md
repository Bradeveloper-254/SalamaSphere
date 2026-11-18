# SalamaSphere Kiswahili offensive-language baseline

This folder contains a local classical NLP experiment. It classifies text according to the general offensive/non-offensive labels in the `metabloit/offensive-swahili-text` dataset. **It is not a TFGBV detector, is not deployed, and must not be used to judge a report's credibility or deny assistance.** Predictions require human review.

## Dataset and limits

The dataset card says the data was scraped from JamiiForums using a prepared abusive-word list; label 0 is non-offensive and label 1 is offensive. The card says sarcasm is not covered. It has no TFGBV-specific taxonomy, detailed annotation rubric, or author/thread/time metadata. The card declares MIT, but source-site permissions for the underlying posts are not documented. Review [Data/DATA_SOURCES.md](Data/DATA_SOURCES.md) before redistributing or considering commercial use.

Run dataset inspection and cleaning from this directory:

```powershell
..\.venv\Scripts\python.exe src\inspect_dataset.py
```

This preserves the downloaded source and writes cleaned CSVs to `Data/processed/` and summary counts to `reports/dataset_quality_report.csv`. Current cleaned row counts are 4,321 train, 970 validation, and 642 test. The cleaner removes blanks, repeated normalized examples, conflicting-label messages, exact cross-split overlaps, and conservative high-similarity cross-split candidates.

## Environment and commands

From `SALAMASPHERE_AI` in PowerShell, activate the environment and install the project dependencies:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r .\tfgbv_text_classifier\requirements-dev.txt
cd .\tfgbv_text_classifier
```

Inspect the existing logistic model's validation errors (message text is saved locally, not printed):

```powershell
python src\inspect_validation_errors.py
```

Recreate the validation-only model comparison (fits on train, selects threshold on validation; does not load test):

```powershell
python src\compare_validation_models.py
```

Run the packaged inference CLI:

```powershell
python src\predict.py --text "Nahitaji msaada tafadhali."
```

Run tests:

```powershell
python -m pytest -q
```

The one-shot final test evaluator has a guard and refuses to overwrite an existing final report:

```powershell
python src\evaluate_final_model.py
```

Do not rerun it or tune from its result. The test set was used in earlier development, so the current test metrics are descriptive, not a pristine independent estimate.

## Current model

Validation selected a word+character TF-IDF `LinearSVC` with a decision threshold of `-0.281890`. The threshold was selected for highest precision subject to at least 70% validation offensive recall. Validation macro F1 was 0.7939, offensive precision 0.8626, and recall 0.7019. The final descriptive test evaluation gave macro F1 0.6455, offensive precision 0.8832, and recall 0.3878 (191 false negatives out of 312 offensive examples). This weak recall is material and is not concealed. See [final evaluation](reports/final_model_evaluation.md).

The score exposed by `src/predict.py` is an unbounded SVM decision margin, not a probability or real-world risk estimate. See [model card](reports/model_card.md) and [data/error analysis](reports/data_and_error_analysis.md).

## Next research steps

The next milestone is an independently sourced, ethically governed TFGBV annotation project, not production integration of this baseline. See [the dataset development plan](reports/tfgbv_dataset_development_plan.md). Any future integration must preserve privacy, uncertainty, human review, and access to assistance regardless of model output.
