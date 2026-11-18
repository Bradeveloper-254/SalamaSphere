# Model card: SalamaSphere Kiswahili offensive-language baseline

## Summary

- **Model version:** `swahili-offensive-linear-svm-clean-v1`
- **Type:** word and character TF-IDF features with `LinearSVC`
- **Status:** research baseline; local inference only; not deployed
- **Selected on:** validation macro F1 with offensive recall constrained to at least 70%
- **Score:** unbounded decision-function margin; not a probability

This model approximates the dataset's general offensive/non-offensive labels. It is **not a TFGBV classifier** and has no validation for survivor support, threat assessment, or case triage.

## Data

The model used 4,321 cleaned training rows from `metabloit/offensive-swahili-text`, with 970 validation rows and 642 test rows. The data source is JamiiForums comments collected by a prepared abusive-word list. The source card defines `0` as non-offensive and `1` as offensive and states that sarcasm is not covered. It offers no detailed annotation guide or TFGBV sublabels and carries no author/thread/time metadata.

The dataset card declares MIT. Underlying forum-post rights and source-site terms are not established by that declaration. See `Data/DATA_SOURCES.md`; review rights and privacy before redistribution or commercial use.

## Training and selection

The selected pipeline uses word TF-IDF n-grams `(1,2)` and character TF-IDF n-grams `(2,5)`, each capped at 50,000 features with `min_df=2` and sublinear TF, followed by balanced `LinearSVC(C=1.0, max_iter=5000, random_state=42)`. The threshold `-0.28189041864009656` maximizes validation precision among thresholds with offensive recall at least 70%.

Validation comparison macro F1: selected LinearSVC 0.7939; logistic regression 0.7669; ComplementNB 0.7266. The test split was not used for these choices. The JSON report is `reports/validation_model_comparison.json`.

## Evaluation

Final one-pass descriptive test results for this selected artifact:

- Accuracy: 0.6776
- Macro F1: 0.6455
- Offensive precision: 0.8832
- Offensive recall: 0.3878
- Confusion matrix (actual rows, predicted columns; labels 0,1): `[[314, 16], [191, 121]]`

The test split was previously examined and used for earlier model evaluations, so these results are not an untouched independent estimate. The false-negative rate for class 1 is 0.6122. This makes the model unsuitable for safety-critical use without substantial new data and evaluation.

## Intended and unsupported use

**Intended:** reproducible offline experimentation, error analysis, and demonstration of a general Kiswahili offensive-language baseline.

**Unsupported:** detecting TFGBV, establishing the truth or severity of a report, identifying a survivor or perpetrator, automated moderation or punishment, prioritizing emergency response, or denying assistance. The model must never replace human judgment.

## Known limitations and failure modes

- Prepared word-list collection and missing sarcasm coverage.
- Informal spelling, Sheng, code-switching, dialect, and context have not been separately annotated or evaluated.
- No metadata for author/thread/time-aware splitting.
- Validation and historical test exposure limit generalization claims.
- High false-negative rate on the final descriptive test pass.
- Decision margins are not calibrated probabilities.
- A high score may reflect a word pattern without understanding quotation, negation, target, intent, or context.

## Privacy and ethical considerations

Do not log raw messages in production. The local validation error CSVs contain text and should remain access-controlled. Minimize retention, obtain appropriate permission for text processing, provide human review, preserve a route to support independent of predictions, and avoid claims that model output constitutes evidence.

## Reproducibility

Run `python src/compare_validation_models.py` to refit train-only candidates and select on validation. Run `python src/predict.py --text "..."` for local inference. Run `python -m pytest -q` for tests. `src/evaluate_final_model.py` is guarded against a second test pass; do not use its result to tune.
