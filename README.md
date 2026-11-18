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
- `mobile/`: companion Flutter application, maintained in the separate `SalamaSphere_Flutter` repository.
- SalamaSphere_device/: Active integrated wearable sketch, hardware inventory, and legacy device prototypes.
- wearable/: Wearable firmware.
- web/: Web interface resources.
- docs/: Architecture and project documentation.
- tests/: Test plans and automated tests.

## Wearable firmware and BLE protocol

For the integrated Flutter prototype, build
`SalamaSphere_device/firmware/production/salamasphere_wearable.ino` (ESP32-S3,
firmware v1.4.2, NimBLE-Arduino 2.5.1). Its service and characteristic UUIDs,
SOS JSON event, and acknowledged WAV transfer protocol match the BLE service
in the companion Flutter app. The older sketch under
`SalamaSphere_device/firmware/ble_communication/` uses a different protocol
and does not connect to the current Flutter BLE client; keep it as a legacy
prototype. The Flutter repository also contains a byte-identical sketch copy;
keep that mirror synchronized with this firmware file.

## Development Status

| Status | Verified scope |
|---|---|
| Implemented in this repository | Django incident/evidence APIs, encrypted evidence storage and SHA-256 verification, transcript retrieval/review, SOS notification workflows, backend tests, and ESP32 wearable firmware. |
| Implemented but not verified in this workspace | Companion Flutter app. It is maintained in a separate repository and is not checked out here. |
| Research prototype | Kiswahili general offensive-language text classifier in `SALAMASPHERE_AI/`. It is not a TFGBV detector and is not integrated into the application. |
| Planned | Ethically governed TFGBV dataset work and any future TFGBV model research. |

Automated tests do not verify delivery through live SMS, voice, or speech providers. See `docs/security_and_data_handling.md` for repository data handling and review limits.

## Security and Privacy

The system is intended to handle sensitive incident
records.

Evidence access, encryption, retention, consent,
and notification permissions must be carefully designed.

The prototype must not be considered a guaranteed
emergency-response service.

## Automatic wearable incident notifications

SOS and wearable incidents are sent to the admin assignment queue and create
SMS and voice notifications for active trusted contacts who separately
consented to each channel. After the incident commits, the Django web service
processes pending notifications directly, so the Render free plan does not
require a separate Celery worker. This synchronous workaround can increase
request latency; a durable background worker is preferred for production. SMS
includes a map link only for contacts who consented to SMS alerts. Voice calls
do not speak the survivor's name or precise coordinates. Audio evidence
uploads do not trigger notification delivery again.

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

Celery remains available for a future deployment with a background worker.
For the Render web service, use `python -m gunicorn config.wsgi:application`
as the start command. See [docs/RENDER_DEPLOYMENT.md](docs/RENDER_DEPLOYMENT.md)
for free-plan behavior and safe recovery instructions.

For a deployment with a paid worker, run Redis and both background processes
from `backend/`:

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
