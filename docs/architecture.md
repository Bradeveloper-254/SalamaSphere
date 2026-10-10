# SalamaSphere System Architecture

## 1. Architecture Overview

SalamaSphere uses a modular architecture consisting
of a wearable device, mobile application, backend API,
database, evidence storage, notification service,
and web dashboard.

## 2. Wearable Layer

Proposed technology:
- ESP32 development board
- C++ firmware
- SOS button
- Microphone
- Local storage
- Bluetooth Low Energy

Responsibilities:
- Detect SOS activation.
- Generate incident identifiers.
- Record audio when configured.
- Store recordings locally.
- Transmit events over BLE.
- Preserve pending data after disconnection.

## 3. Mobile Application Layer

Proposed technology:
- Android application
- BLE APIs
- Local protected storage
- HTTPS communication

Responsibilities:
- Connect to registered wearables.
- Receive SOS events.
- Receive audio files.
- Obtain available phone location.
- Queue pending incidents.
- Upload incident data.
- Retry synchronization.

## 4. Web Application Layer

Proposed technology:
- Django templates
- HTML
- CSS
- JavaScript

Responsibilities:
- Incident reporting.
- Incident review.
- Evidence verification interface.
- Authorized dashboards.
- User and contact management.

## 5. Backend Layer

Proposed technology:
- Python
- Django
- Django REST Framework

Responsibilities:
- Authenticate users and devices.
- Validate incident requests.
- Prevent duplicate event creation.
- Store incident metadata.
- Manage evidence references.
- Calculate SHA-256 hashes.
- Initiate notifications.
- Maintain audit logs.

## 6. Database Layer

Proposed technology:
- PostgreSQL

Main entities:
- Users
- Wearable devices
- Incidents
- Evidence files
- Notifications
- Synchronization records
- Audit events

## 7. Evidence Storage

Evidence files shall be stored separately from
ordinary relational database records.

The database shall store evidence metadata,
storage references, hashes, and verification status.

Encryption and access controls shall protect evidence.

## 8. Notification Layer

The backend shall integrate with supported SMS
or push-notification services.

Notifications shall be sent to configured authorized
contacts according to the system's response policy.

## 9. Threat Analysis Layer

The initial version shall support user-selected
threat levels and simple classification rules.

Advanced localized NLP shall be introduced after
the core incident workflow has been validated.

## 10. Communication Flow

Wearable -> BLE -> Mobile Application
Mobile Application -> HTTPS -> Django API
Django API -> PostgreSQL
Django API -> Encrypted Evidence Storage
Django API -> Threat Analysis
Django API -> Notification Service
Django API -> Web Dashboard

## 11. Offline Strategy

The wearable shall preserve recordings locally.

The mobile application shall queue incidents when
internet connectivity is unavailable.

Pending incidents shall synchronize when connectivity
returns.

A successful upload shall be acknowledged before
the device considers the data safely synchronized.

## 12. Security Principles

- Device registration and authentication.
- User authentication and authorization.
- Encryption in transit and at rest.
- Restricted evidence access.
- Audit logging.
- Defined retention policies.
- Secure handling of credentials.

## 13. Future Architecture Extensions

- Independent cellular communication.
- Standalone GPS.
- Localized NLP models.
- Optional distributed evidence anchoring.