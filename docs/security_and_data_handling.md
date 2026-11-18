# Security and data handling review

## Scope and findings

This review covers the checked out SalamaSphere repository and the current public `main` snapshot. The repository contains Django backend source, the experimental Kiswahili text classifier, wearable firmware, and documentation. The companion Flutter project is a separate public repository and is not present in this workspace, so its code and tests were not locally audited.

The backend has authentication and ownership checks for evidence, encrypted evidence storage, SHA-256 verification, access audit records, transcript retrieval and human correction endpoints, and a mocked-provider transcription test suite. SOS notification services and callbacks are implemented in source; they are not proof of delivery through live SMS or voice providers. The AI project is an experimental general offensive-language baseline, not a TFGBV detector.

## Dataset and text-bearing reports

The current Git index audit found the three processed split CSVs are not tracked; matching local files are ignored by `.gitignore`. The two validation misclassification CSV reports are tracked in the current `HEAD`. They contain source text and should be treated as restricted research artifacts. This finding corrects earlier wording in this document that said they had been removed from the Git index. Do not print, copy, or publish their rows. Their blobs also occur in repository history. No history rewrite or remote change was performed in this work; coordinate any history cleanup separately.

The dataset card declares MIT, but says the posts were scraped from JamiiForums. The uploader's declaration does not establish rights to redistribute each underlying post. Until source-site terms and privacy/rights questions are resolved, public redistribution is not justified. Keep local copies restricted to authorized research and reassess artifact provenance before distribution.

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
