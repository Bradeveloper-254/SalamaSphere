# Emergency audio speech-to-text

The authenticated endpoint `POST /api/evidence/<evidence_id>/transcribe/` decrypts an authorized user's original audio in memory, checks its stored plaintext SHA-256, and submits a copy to the configured OpenAI transcription API. The original evidence file and its hash are not modified. Transcripts and their processing metadata live in `EvidenceTranscript` rows separately.

Submit JSON `{ "language": "auto" }` for automatic detection, or `sw` / `en` for a user-selected language. The stored `language_source` records which path was used. Supported targets are Kiswahili and English. No Sheng support is claimed; it needs evaluation on representative Sheng recordings. Every transcript has `human_review_required=true`; recognition is an aid for review and does not classify danger or establish that violence occurred.

Configure `OPENAI_API_KEY` and optionally `SPEECH_TO_TEXT_MODEL` (defaults to `whisper-1`) on the backend. Apply migrations with `python manage.py migrate`. Audio is sent to the configured speech provider; account and provider data handling requirements should be reviewed before production use. No audio or transcript is written to application logs.

The transcript is returned to the authorized caller and is stored in the database. Authorized users can retrieve a transcript history with `GET /api/evidence/<evidence_id>/transcripts/` and submit a human correction with `PUT /api/transcripts/<transcript_id>/review/` and `{ "transcript": "corrected words" }`. Corrections are stored separately; the original machine transcript remains unchanged and each correction is retained in revision history. Requests run synchronously and are subject to application/provider request timeouts. Recognition can be inaccurate, especially for code-switching, noise, and Sheng.

The companion Flutter repository is separate and is not checked out in this workspace. Flutter integration was therefore not locally inspected or tested as part of this review.

## Demonstration

1. Record or select a short Kiswahili audio file and upload it to an incident through the authenticated evidence endpoint. Submit the original bytes' SHA-256 and `sha256_hash_type=plaintext` as required by the upload API.
2. Call the transcription endpoint for its returned evidence ID with `{"language":"sw"}`; inspect the response status and transcript, then have a fluent speaker review it.
3. Repeat with a clear English recording and `{"language":"en"}`.
4. To test automatic selection, send `{"language":"auto"}` and confirm `language_source` is `automatic`; user-selected requests report `user_selected`.
5. Automated tests mock the provider and make no paid API calls. A live demonstration requires a valid provider API key and makes an external request.
