# SalamaSphere System Requirements

## 1. Project Overview

SalamaSphere is a decentralised, offline-first incident
logging and evidence-preservation system designed to
support survivors of technology-facilitated gender-based
violence (TFGBV).

The system combines a wearable safety device, mobile
application, web application, backend API, database,
evidence storage, and threat-analysis capabilities.

## 2. Main Objectives

1. Enable discreet SOS activation through a wearable.
2. Capture and preserve incident audio when enabled.
3. Transfer incident information to a mobile application.
4. Record available location information.
5. Store incident records securely.
6. Verify evidence-file integrity using SHA-256.
7. Notify authorized contacts about SOS incidents.
8. Preserve incidents during internet interruptions.
9. Provide authorized incident-management dashboards.
10. Introduce localized threat analysis in later versions.

## 3. Functional Requirements

### FR1: User Management
The system shall authenticate users and enforce
role-based permissions.

### FR2: Device Registration
The system shall associate authorized wearable devices
with registered users.

### FR3: SOS Activation
The wearable shall generate an incident event when
the configured SOS activation pattern is detected.

### FR4: Audio Recording
The wearable shall capture audio after activation
according to the configured recording policy.

### FR5: Local Storage
The wearable shall retain recordings until they are
safely synchronized or removed under the retention policy.

### FR6: Bluetooth Communication
The wearable shall transmit incident events to the
registered mobile application over BLE.

### FR7: Location Collection
The mobile application shall attach available location
information with its source, timestamp, and accuracy.

### FR8: Incident Logging
The backend shall create and maintain incident records.

### FR9: Evidence Storage
The system shall store evidence securely and associate
each file with its incident record.

### FR10: Evidence Integrity
The backend shall calculate and verify SHA-256 hashes
for completed evidence files.

### FR11: Threat Classification
The system shall support low, medium, and high threat
levels, with user review and later NLP enhancement.

### FR12: Emergency Notifications
The backend shall notify configured authorized contacts
through supported notification channels.

### FR13: Offline Operation
The mobile application shall queue incident data when
internet access is unavailable.

### FR14: Synchronization
The application shall synchronize pending incidents
when connectivity returns.

### FR15: Dashboard
Authorized users shall be able to view permitted
incident information and its processing status.

### FR16: Audit Logging
The system shall record important evidence-access
and incident-management actions.

## 4. Non-Functional Requirements

### Security
The system shall authenticate devices and users,
restrict evidence access, and protect data in transit
and at rest.

### Privacy
The system shall minimize data collection and follow
defined consent, access, and retention policies.

### Reliability
The system shall preserve pending incidents during
connectivity failures and retry synchronization safely.

### Integrity
The system shall detect changes to files after their
original hashes have been recorded.

### Usability
The SOS activation process shall be understandable
and usable under stressful conditions.

### Performance
The system shall process incident metadata efficiently
and support resumable evidence uploads.

### Maintainability
The codebase shall separate hardware firmware, mobile
integration, backend services, and user interfaces.

## 5. MVP Scope

The first prototype shall include:

- Wearable SOS button.
- Audio recording and local storage.
- BLE communication.
- Mobile application integration.
- Django REST API.
- PostgreSQL database.
- Audio upload and SHA-256 verification.
- Available location collection.
- Basic threat classification.
- Test emergency notifications.
- Incident dashboard.
- Offline synchronization.

## 6. Future Enhancements

- Independent cellular SOS communication.
- Standalone wearable GPS.
- Localized Sheng and Swahili NLP.
- Audio transcription.
- Advanced threat analysis.
- Additional emergency-response integrations.
- Optional distributed evidence anchoring.

## 7. Limitations

A Bluetooth-only wearable cannot independently
send remote alerts when the registered phone is
unavailable.

An offline device cannot deliver a live internet
notification without an available communication path.

SHA-256 verification checks file integrity but does
not independently prove that an event occurred
exactly as described.