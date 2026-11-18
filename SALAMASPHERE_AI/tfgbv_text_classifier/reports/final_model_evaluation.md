# Final model evaluation

**Model:** SalamaSphere Kiswahili offensive-language baseline (`swahili-offensive-linear-svm-clean-v1`)  
**Test examples:** 642  
**Score threshold:** -0.281890 LinearSVC decision margin (not a probability)

| Metric | Result |
|---|---:|
| Accuracy | 0.6776 |
| Macro F1 | 0.6455 |
| Offensive precision | 0.8832 |
| Offensive recall | 0.3878 |
| Offensive false-negative rate | 0.6122 |
| Non-offensive false-positive rate | 0.0485 |

Confusion matrix (actual rows, predicted columns; labels 0, 1): `[[314, 16], [191, 121]]`.

## Comparison with earlier artifacts

| Artifact/result | Test accuracy | Macro F1 | Offensive precision | Offensive recall | Confusion matrix |
|---|---:|---:|---:|---:|---|
| Earlier tuned Logistic Regression (historical report) | 0.7056 | 0.6842 | 0.8773 | 0.4583 | `[[310, 20], [169, 143]]` |
| Earlier Linear SVM (historical report) | 0.6667 | 0.6284 | 0.8952 | 0.3558 | `[[317, 13], [201, 111]]` |
| Selected cleaned-train Linear SVM (this report) | 0.6776 | 0.6455 | 0.8832 | 0.3878 | `[[314, 16], [191, 121]]` |

The earlier model results use the same historically exposed test split and older fitted artifacts. The selected model was chosen on validation before this single final pass. Its test performance is below the earlier tuned logistic result; this was not used to switch models or retune the threshold.

## Evaluation limitation

This test split was previously used for evaluation/error analysis of earlier model artifacts. These results are a single final descriptive evaluation, not an untouched independent estimate. Do not tune from these results.

This is a general offensive-language baseline, not a validated TFGBV detection system. The score is a decision margin, not a calibrated probability or real-world risk estimate. See `data_and_error_analysis.md` for dataset and historical result context.
