# Data and validation error analysis

## Dataset definition and scope

The source is `metabloit/offensive-swahili-text`, whose Hugging Face card labels `0` as non-offensive and `1` as offensive. The card describes JamiiForums comments collected with a prepared abusive-word list and explicitly says sarcastic abuse is not covered. It does not publish a detailed annotation rubric, annotator agreement, source/user/time identifiers, or labels for threats, sexual harassment, misogyny, or TFGBV. The label therefore means the dataset's general offensive-language category, not TFGBV.

The card declares MIT. Because the comments were scraped from a third-party forum and rights/terms clearance is not described, treat MIT as uploader-declared and do not redistribute or use commercially until source terms and rights have been reviewed. See [DATA_SOURCES.md](../Data/DATA_SOURCES.md).

## Dataset quality

The raw splits were balanced by label. Inspection found blank messages, repeated examples, one contradictory training label, and cross-split duplicates. The cleaner now removes blanks, normalized duplicates, all occurrences of contradictory-label messages, exact cross-split overlaps, and conservative near-duplicate overlaps. Near duplicates are flagged only when both character 3–5 gram cosine similarity and sequence similarity are at least 0.90. Held-out test rows take precedence over validation, and both held-out splits take precedence over training. The Hugging Face source files are not modified.

| Split | Raw | Blank | Exact duplicate rows | Normalized duplicate rows | Conflicting-label rows | Near-duplicate rows removed | Clean | Class 0 / class 1 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Train | 4,954 | 4 | 282 | 279 | 2 | 3 | 4,321 | 2,264 / 2,057 |
| Validation | 990 | 1 | 19 | 19 | 0 | 0 | 970 | 487 / 483 |
| Test | 660 | 0 | 18 | 18 | 0 | 0 | 642 | 330 / 312 |

The cleaned train split is mildly imbalanced (52.4% class 0, 47.6% class 1); validation and test are close to balanced. Character 3–5 gram nearest-neighbor checks found a small number of very similar cross-split rows, with three training rows removed. The post-clean normalized text overlap is zero for every split pair, and no cross-split candidate remains above the dual 0.90 similarity threshold. The check also flagged 9 train, 4 validation, and 2 test rows with a high-similarity neighbor inside their own split; these were retained for manual review because similarity alone does not establish duplication. Approximate similarity is a heuristic; the threshold is documented in `src/inspect_dataset.py` and should be reviewed for future datasets.

Each split contains only `text` and `labels`. There is no author, source-thread, or timestamp field, so author-aware, thread-aware, or time-aware partitioning cannot be performed without inventing metadata.

Text lengths are short: clean train median 11 whitespace tokens and validation median 10. The validation split has 125 messages of at most three tokens, 83 with a character repeated three or more times, 56 containing punctuation, and 3 containing digits. These are surface-form counts, not linguistic labels. The available schema does not identify Sheng, code-switching, sarcasm, gendered abuse, threats, or context. We do not claim these categories were measured reliably; Kiswahili-speaking annotators should review them before making language-specific conclusions.

## Existing logistic validation error inspection

`src/inspect_validation_errors.py` was run against the existing word/character logistic artifact (historically trained on 4,324 rows, before three near-duplicate train rows were removed) at the recorded validation threshold 0.3443636. It prints aggregate metrics only and saves message text in the local `reports/validation_misclassified.csv` for controlled review.

- Validation examples: 970; confusion matrix (rows actual, columns predicted; labels 0,1): `[[413, 74], [142, 341]]`.
- False negatives: 142; false positives: 74; macro F1: 0.7761.
- False negatives had median 44 characters / 7 whitespace tokens; false positives had median 180 characters / 28 tokens. This describes this model's errors, not a causal explanation.
- The probability distributions and word/character overlap do not determine whether these mistakes involve slang, sarcasm, indirect insults, or context. No reliable category annotations exist in the dataset.

After selecting the cleaned-train Linear SVM by validation, its validation errors were also saved to `reports/selected_model_validation_misclassified.csv`. At its decision threshold, it had 144 false negatives and 54 false positives; the confusion matrix is `[[433, 54], [144, 339]]` and macro F1 is 0.7939. Its total error count is 198/970.

## Validation-only model and preprocessing comparison

New candidates were fitted on the cleaned train split and selected using validation only. All candidates used the same threshold rule: highest precision subject to offensive recall of at least 70%. The test split was not loaded during these experiments.

| Candidate | Validation threshold | Offensive precision | Offensive recall | Macro F1 |
|---|---:|---:|---:|---:|
| Word + character TF-IDF, Linear SVM | -0.281890 (decision margin) | 0.8626 | 0.7019 | **0.7939** |
| Word + character TF-IDF, char_wb Logistic Regression | 0.327875 | 0.8129 | 0.7019 | 0.7699 |
| Word + character TF-IDF, Logistic Regression | 0.334695 | 0.8071 | 0.7019 | 0.7669 |
| NFKC + whitespace normalization, same Logistic features | 0.334671 | 0.8071 | 0.7019 | 0.7669 |
| Word + character TF-IDF, ComplementNB | 0.500000 | 0.7370 | 0.7019 | 0.7266 |

Unicode/whitespace normalization alone made no material difference in this run. The char_wb configuration raised macro F1 by about 0.003 over the comparable logistic baseline; this is a small validation gain. ComplementNB was weaker. The Linear SVM is selected on validation macro F1 with the predeclared 70% minimum recall criterion. Do not interpret a LinearSVC margin as a probability.

For probability-producing logistic candidates, validation Brier scores were about 0.183 and 10-bin expected calibration errors about 0.183. These diagnostics do not establish calibrated deployment probabilities. The selected SVM has no probability output and was not calibrated.

## Test-set status

The test split was already used by the earlier development work for model evaluation and error analysis, and earlier raw splits had leakage. The final selected model will be evaluated once for documentation, but the score must be treated as descriptive rather than an untouched independent estimate. Do not tune from that result. A genuinely independent evaluation requires a new, source-aware, expert-reviewed holdout.
