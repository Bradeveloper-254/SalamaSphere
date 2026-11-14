# SalamaSphere

### A Decentralised, Offline-First Incident Logging
### and AI Evidence Vault for TFGBV Survivors

## Overview

SalamaSphere is a proposed safety and evidence-preservation
system designed to support survivors of technology-
facilitated gender-based violence.

The system combines a wearable SOS device, mobile
application, web application, backend API, secure evidence
storage, threat analysis, and emergency notifications.

## Problem Statement

Survivors may be unable to access their phones during
dangerous situations, while digital evidence can be
lost, altered, or difficult to preserve.

SalamaSphere aims to provide a discreet method of
initiating incidents, recording evidence when configured,
preserving incident records, and notifying authorized
contacts.

## Main Features

- Wearable SOS activation.
- Audio recording and local storage.
- Bluetooth communication.
- Mobile application integration.
- Offline incident synchronization.
- Location-aware incident reporting.
- SHA-256 evidence integrity verification.
- Authorized incident dashboards.
- Emergency notifications.
- Future localized threat analysis.

## Technology Stack

- Python
- Django
- Django REST Framework
- PostgreSQL
- C++
- ESP32
- Bluetooth Low Energy
- Android
- HTML, CSS, JavaScript
- SHA-256

## Project Structure

- backend/: Server-side application.
- mobile/: Mobile application.
- SalamaSphere_device/: Wearable firmware, hardware inventory, and device documentation.
- wearable/: Wearable firmware.
- web/: Web interface resources.
- docs/: Architecture and project documentation.
- tests/: Test plans and automated tests.

## Development Status

Day 1: Project planning and architecture.

Subsequent milestones include backend development,
wearable programming, mobile integration, evidence
preservation, notifications, and testing.

## Security and Privacy

The system is intended to handle sensitive incident
records.

Evidence access, encryption, retention, consent,
and notification permissions must be carefully designed.

The prototype must not be considered a guaranteed
emergency-response service.

## Automatic wearable incident SMS

SOS and wearable incidents are sent to the admin assignment queue and create
SMS and voice notifications for active trusted contacts who separately
consented to each channel. After the incident commits, Celery queues delivery
so provider latency does not delay the incident response. SMS includes a map
link only for contacts who consented to SMS alerts. Voice calls do not speak
the survivor's name or precise coordinates.

The mobile app registers a wearable identifier to the signed-in user before
syncing its SOS incident. Repeated registration by the same account reuses an
active registration; inactive devices and identifiers owned by another
account cannot be claimed.

Mobile Sasa is the default SMS provider. Configure these backend environment
variables before deployment:

- `SMS_PROVIDER=mobile_sasa`
- `MOBILESASA_TOKEN`: Mobile Sasa API token.
- `MOBILESASA_SENDER_ID`: sender ID registered with Mobile Sasa.
- `MOBILESASA_BASE_URL`: Mobile Sasa API origin; defaults to
  `https://api.mobilesasa.com`.

Keep provider tokens in the deployment secret store, not source control.
Set `SMS_PROVIDER=console` to simulate SMS locally, or select `twilio` or
`esms_africa` to use an alternate configured provider. An accepted response
confirms submission to the provider, not delivery to the handset.

Run Redis, then run both background processes from `backend/`:

```text
celery -A config worker --loglevel=INFO
celery -A config beat --loglevel=INFO
```

`CELERY_BROKER_URL` defaults to `redis://127.0.0.1:6379/0`. Beat re-enqueues
pending notifications and changes stale `processing` records to `unknown`
without redialing them; provider callbacks can still reconcile a recorded
call session later. To process one pending alert explicitly, run
`python manage.py process --notification-id <notification-uuid>`.

To enable Africa's Talking voice calls, configure `AT_VOICE_MODE=africas_talking`,
`AT_VOICE_USERNAME`, `AT_VOICE_API_KEY`, and `AT_VOICE_NUMBER`. Set
`AT_VOICE_CALLBACK_TOKEN` to a high-entropy secret and configure
`AT_VOICE_CALLBACK_URL` as the public HTTPS callback URL with that exact token
in its `?token=` query parameter. Register the URL with the Africa's Talking
Voice application so it can play the announcement and report call progress.
`accepted` means the provider queued the call; callbacks distinguish ringing,
answered, completed, and failed outcomes.

## Documentation

See the docs/ directory for requirements, architecture,
API planning, and testing documentation.


## Development Status

### Day 1
- Project structure established.
- Initial system requirements documented.
- Software architecture documented.
- Git repository configured.

### Day 2
- Django project created.
- Django REST Framework installed.
- PostgreSQL configured.
- Custom user model implemented.
- Wearable device model implemented.
- Incident model implemented.
- Evidence model implemented.
- Notification model implemented.
- Threat assessment model implemented.
- Django administration configured.
- Initial automated tests created.

### Next Milestones
- Device registration and authentication.
- Incident management APIs.
- Evidence upload and integrity verification.
- Notification integration.
- Mobile application integration.
- Wearable firmware development.

## Device BLE Protocol UUIDs

We'll use this service UUID:

7b6a0001-7d42-4a8e-9b31-2f4c8a6e1000

And these characteristic UUIDs:

Device Identity:
7b6a0002-7d42-4a8e-9b31-2f4c8a6e1000

SOS Event:
7b6a0003-7d42-4a8e-9b31-2f4c8a6e1000

Recording Status:
7b6a0004-7d42-4a8e-9b31-2f4c8a6e1000

Audio Metadata:
7b6a0005-7d42-4a8e-9b31-2f4c8a6e1000

Audio Transfer Control:
7b6a0006-7d42-4a8e-9b31-2f4c8a6e1000

Audio Data:
7b6a0007-7d42-4a8e-9b31-2f4c8a6e1000

Transfer Acknowledgement:
7b6a0008-7d42-4a8e-9b31-2f4c8a6e1000

Battery Status:
7b6a0009-7d42-4a8e-9b31-2f4c8a6e1000
