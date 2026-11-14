# SalamaSphere API Specification

## Authentication

POST /api/auth/login/
POST /api/auth/logout/

## Device Management

POST /api/devices/register/
GET  /api/devices/
GET  /api/devices/{device_id}/

## Incident Management

POST /api/incidents/
GET  /api/incidents/
GET  /api/incidents/{incident_id}/
POST /api/incidents/{incident_id}/threat-assessments/
POST /api/threat-assessments/{assessment_id}/review/

## Evidence Management

POST /api/incidents/{incident_id}/audio/
GET  /api/incidents/{incident_id}/evidence/
GET  /api/incidents/{incident_id}/evidence/verify/
GET  /api/evidence/{evidence_id}/file/

## Location

POST /api/incidents/{incident_id}/location/

## Synchronization

POST /api/incidents/{incident_id}/sync/

## Notifications

GET   /api/notifications/
GET   /api/notifications/?incident={incident_id}
PATCH /api/notifications/{notification_id}/
GET   /api/notifications/messages/recipients/
POST  /api/notifications/messages/
POST  /api/trusted-contacts/
DELETE /api/trusted-contacts/{contact_id}/

The notification detail PATCH accepts `{"is_read": true|false}` and is
restricted to the notification recipient.
The messaging endpoints are for active, approved authorities. They can message
administrators or survivors with a case assigned to them; the resulting message
is delivered to the recipient's in-app notification inbox.
Creating a trusted contact with SOS alerts enabled requires
`confirm_sos_consent: true`, confirming the user has permission to send those
alerts. Automated voice calls are separately disabled by default; enabling
`receive_voice_calls` requires `confirm_voice_consent: true`. SMS consent does
not enable voice calls. Deleting a contact with retained delivery history
deactivates it.

## Authority Case Workflow

GET  /api/incidents/admin/unassigned/
GET  /api/incidents/admin/assignments/available-authorities/?incident_id={incident_id}
POST /api/incidents/admin/assignments/
GET  /api/incidents/authority/assigned/
POST /api/incidents/authority/presence/
POST /api/incidents/authority/assigned/{incident_id}/resolve/

Authorities must be approved, available, and without an active assignment.
When an incident has coordinates, candidates also need a location updated
within the previous 24 hours and are returned nearest-first within 100 km.
When the incident has no coordinates, any otherwise eligible authority is
returned with a `null` candidate distance. Resolving a case closes its
incident and releases its active assignment.

The web incident form requests device location through the browser when the
form opens and refreshes it immediately before submission. It sends captured
coordinates, accuracy, and the location source with the incident. Browser
location permission remains under the user's control, and location access
requires a secure context such as HTTPS or localhost. When location is denied
or unavailable, the user may retry or explicitly submit without coordinates.

## Authority Verification Documents

GET /api/accounts/admin/verification-documents/
GET /api/accounts/admin/verification-documents/{document_id}/download/

Both endpoints require administrator authorization. Verification files are
returned through the authenticated download endpoint rather than public URLs.

## Notes

The notification and authority workflow endpoints above are implemented.
Some other paths in this high-level specification may need reconciliation
with the current URL configuration before use.

Incident creation requires an authenticated user. Wearable-origin incidents
must include the identifier of an active wearable owned by that user. Mobile
SOS events may be submitted without a wearable. Eligible, consented trusted
contacts are queued for SOS SMS with the incident severity and a map link when
coordinates were captured. Contacts who separately opt in to automated voice
calls are queued for mock-mode calls by default. The server stores an initial
rules-based threat assessment and
raises the stored priority when supported keywords or explicit indicators
suggest a higher level; assessments flagged by the rules require human review.
Keyword checks are a triage aid, not a validated risk prediction.
Device authorization checks that the authenticated user owns an active
registered wearable. The wearable identifier is not a cryptographic
proof-of-possession; stronger hardware authentication requires a
provisioned device key and signed requests.

Evidence uploads are hashed as plaintext, encrypted with AES-256-GCM before
being written to private media storage, and decrypted only after an integrity
check on authorized downloads. Existing evidence rows remain marked as
unencrypted until migrated; run `python manage.py encrypt_legacy_evidence`
during a maintenance window to migrate them, and review any reported failures.
Configure a stable, URL-safe-base64-encoded
32-byte `EVIDENCE_ENCRYPTION_KEY` in the backend environment and back it up
securely; if unset, the key is derived from Django's `SECRET_KEY`. Rotating
either key without re-encrypting stored files makes encrypted evidence
unreadable. Generate a dedicated key with
`python -c "import base64, os; print(base64.urlsafe_b64encode(os.urandom(32)).decode())"`
and keep it in the backend secret store, not source control.

Incident creation, evidence upload/access/verification, and threat assessment
actions are recorded in the incident audit log. New incidents, assignments,
resolutions, account and document reviews, and evidence uploads create
recipient-specific in-app notifications. Authorities and administrators
receive an idempotent reminder for assignments still active after 14 days;
the reminder is created when the inbox is read or by running
`python manage.py remind_overdue_cases` on a daily schedule. The configured
SMS provider is currently simulated; production SMS delivery requires a real
provider and a running `python manage.py process` worker. Device push delivery
is not configured.