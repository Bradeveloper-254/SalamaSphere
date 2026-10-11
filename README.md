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