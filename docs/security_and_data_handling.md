# Security and data handling review

## Scope and findings

This review covers the checked out SalamaSphere repository and the current public `main` snapshot. The repository contains Django backend source, the experimental Kiswahili text classifier, wearable firmware, and documentation. The companion Flutter project is a separate public repository and is not present in this workspace, so its code and tests were not locally audited.

The backend has authentication and ownership checks for evidence, encrypted evidence storage, SHA-256 verification, access audit records, transcript retrieval and human correction endpoints, and a mocked-provider transcription test suite. SOS notification services and callbacks are implemented in source; they are not proof of delivery through live SMS or voice providers. The AI project is an experimental general offensive-language baseline, not a TFGBV detector.

## Public repository data cleanup

The following tracked files contain raw user-generated forum messages or excerpts and are removed from the Git index. Their local copies are retained and ignored for future staging:

- `SALAMASPHERE_AI/tfgbv_text_classifier/Data/processed/train.csv` — full message text in training examples.
- `SALAMASPHERE_AI/tfgbv_text_classifier/Data/processed/validation.csv` — full message text in validation examples.
- `SALAMASPHERE_AI/tfgbv_text_classifier/Data/processed/test.csv` — full message text in held-out examples.
- `SALAMASPHERE_AI/tfgbv_text_classifier/reports/validation_misclassified.csv` — text-bearing prediction errors.
- `SALAMASPHERE_AI/tfgbv_text_classifier/reports/selected_model_validation_misclassified.csv` — text-bearing prediction errors.

The dataset card declares MIT, but says the posts were scraped from JamiiForums. The uploader's declaration does not establish rights to redistribute each underlying post. Until source-site terms and privacy/rights questions are resolved, public redistribution is not justified. The five files remain available in this local checkout for authorized research. Their Git blobs remain accessible in existing history and on clones until a separately planned history rewrite is approved and coordinated; no history was rewritten and no remote change was made here.

Aggregate metrics, model code, source instructions, and non-text-bearing reports remain tracked. Model artifacts remain because they are needed for local inference and do not contain the source rows directly. Reassess artifact provenance and licensing before distribution or deployment.

## Credentials and local data

The local backend `.env` is ignored by Git and contains configured credentials. Values were not included in this report. No confirmed live credential was found in current tracked source; historical secret-pattern hits were in test fixtures and need a human check if those fixtures ever contain non-placeholder values. If any credential was real, revoke it and issue a replacement. Keep deployment values in a secret manager.

`backend/private_media/` contains ignored local evidence/test documents. It was not opened, copied, or deleted during this review. Keep it outside source control and apply access controls and retention rules appropriate to incident evidence.

Backend environment variables include `DJANGO_SECRET_KEY`, `EVIDENCE_ENCRYPTION_KEY`, database settings (`DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`), `OPENAI_API_KEY` and optionally `SPEECH_TO_TEXT_MODEL`, SMS provider settings (`SMS_PROVIDER`, `MOBILESASA_TOKEN`, `MOBILESASA_SENDER_ID`, `MOBILESASA_BASE_URL`, or provider-specific credentials), and Africa's Talking voice settings (`AT_VOICE_MODE`, `AT_VOICE_USERNAME`, `AT_VOICE_API_KEY`, `AT_VOICE_NUMBER`, callback URLs and callback token). Only configure providers that are in use. Never place keys in Flutter or public source.

`EVIDENCE_ENCRYPTION_KEY` must be URL-safe base64 encoding exactly 32 bytes. `OPENAI_API_KEY` is required only when live speech recognition is enabled; automated tests mock the provider.

Set a stable, separately generated `EVIDENCE_ENCRYPTION_KEY` before storing production evidence. The backend can derive a fallback from `DJANGO_SECRET_KEY`; changing that fallback key makes older encrypted evidence unreadable unless the key is preserved. Back up the encryption key separately from the database and test recovery before rotating it.

## Data handling rules

- Keep raw text, transcripts, audio, incident details, direct identifiers, and text-bearing error samples private by default.
- Restrict access to incident evidence by owner/authorized role and retain an audit trail.
- Do not place message text, transcripts, credentials, or precise survivor location in logs, analytics, public examples, or model reports.
- Keep a source, license/permission, consent, retention, and deletion record for every future dataset.
- Recheck `.gitignore` and staged changes before committing data-related work.
- Do not treat the general offensive-language classifier as a TFGBV finding, risk score, evidence assessment, or reason to delay assistance.

## Test and deployment notes

Backend tests can be run with mock SMS/voice configuration and a disposable database. Do not run integration scripts that target a live service or send real notifications as part of a routine test run. Automated speech tests mock the external transcription provider; no paid request is needed. A successful mock does not establish live recognition quality.

Any Git history cleanup would invalidate existing commit IDs and require coordinated force updates and fresh clones. This review only stages removal of the five current tracked copies; it does not rewrite history, commit, or push.
