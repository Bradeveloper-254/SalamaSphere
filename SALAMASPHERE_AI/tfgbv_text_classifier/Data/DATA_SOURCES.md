# Dataset source, label meaning, and use conditions

## Source

- Hugging Face dataset: [`metabloit/offensive-swahili-text`](https://huggingface.co/datasets/metabloit/offensive-swahili-text)
- Dataset card says the examples were scraped from JamiiForums using a prepared word list.
- The card says the dataset includes sentences containing abusive Swahili words from that list and does not cover sarcastic abuse.
- Dataset card splits: train (4,954), validation/evaluation (990), test (660); columns: `text`, `labels`.

## What the labels mean

The card defines `0` as `non-offensive` and `1` as `offensive`. It does not provide a detailed annotation rubric, annotator process, agreement score, or definitions for harassment, hate speech, threats, sexual abuse, or gender based violence. The prepared-word-list collection method means the positive class is best understood as *offensive language as operationalized by this dataset*, not a validated TFGBV label. It may miss contextual, coded, sarcastic, or newly emerging abuse and can label quoted or reclaimed language without context.

Do not describe a model trained on this source as a TFGBV detector without new domain-specific annotation and evaluation.

## License and intended use

The Hugging Face dataset page declares the license as **MIT**. This is the uploader-declared dataset license and, on its face, permits reuse, modification, distribution, and commercial use subject to the MIT notice/attribution and warranty terms. However, the dataset card says the text was scraped from JamiiForums and does not document the source site's terms, author permissions, or rights clearance for the underlying user posts. The MIT declaration alone does not establish that the uploader had authority to license every post. Before redistributing the data or using it in a deployed or commercial service, review the source site's terms and applicable rights/privacy requirements; retain attribution and the license notice.

This note records dataset metadata, not a legal determination.

## Quality cleaning performed

Run `python src/inspect_dataset.py` from this project directory. It writes de-duplicated data to `Data/processed/{train,validation,test}.csv` and a count report to `reports/dataset_quality_report.csv`. Empty rows, within-split normalized duplicates, globally conflicting-label messages, and train/held-out overlap are removed. It also removes cross-split candidate near-duplicates only when both character 3–5 gram cosine similarity and sequence similarity are at least 0.90; inspect these criteria for false matches before using the output. Within-split near-neighbor candidates are reported for review but retained. Test rows take precedence over validation rows, and both held-out splits take precedence over training rows. The raw Hugging Face source is not modified.
