# SalamaSphere Testing Plan

## 1. Wearable Tests

- Verify SOS button activation.
- Verify unique event generation.
- Verify timestamp recording.
- Verify audio capture.
- Verify local audio storage.
- Verify BLE event transmission.
- Verify behavior during disconnection.

## 2. Mobile Application Tests

- Verify wearable pairing.
- Verify event reception.
- Verify audio transfer.
- Verify location collection permissions.
- Verify offline queueing.
- Verify upload retries.
- Verify duplicate-event prevention.

## 3. Backend Tests

- Verify user authentication.
- Verify device authentication.
- Verify incident creation.
- Verify request validation.
- Verify database persistence.
- Verify evidence upload.
- Verify SHA-256 generation.
- Verify duplicate-event handling.

## 4. Notification Tests

- Verify configured recipients.
- Verify notification submission.
- Verify delivery-status handling.
- Verify retry behavior.
- Verify privacy-conscious message content.

## 5. Evidence Tests

- Verify file hashing.
- Verify successful integrity checks.
- Verify detection of modified test files.
- Verify access restrictions.
- Verify audit logging.

## 6. Offline Tests

- Disconnect the phone from the internet.
- Create a test incident.
- Verify local retention.
- Restore connectivity.
- Verify synchronization.
- Verify that duplicate incidents are not created.

## 7. Security Tests

- Attempt unauthorized evidence access.
- Test invalid device credentials.
- Test invalid API requests.
- Verify secret exclusion from Git.
- Verify that recordings are not publicly accessible.

## 8. Deployment Readiness

Production deployment requires additional security,
privacy, usability, reliability, and operational testing.

A successful prototype does not guarantee reliable
emergency response under all conditions.