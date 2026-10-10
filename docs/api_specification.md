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

## Evidence Management

POST /api/incidents/{incident_id}/audio/
GET  /api/incidents/{incident_id}/evidence/
GET  /api/incidents/{incident_id}/evidence/verify/

## Location

POST /api/incidents/{incident_id}/location/

## Synchronization

POST /api/incidents/{incident_id}/sync/

## Notifications

GET  /api/incidents/{incident_id}/notifications/

## Notes

These endpoints are proposed interfaces.

Authentication, permissions, request validation,
file-size limits, duplicate-event protection, and
secure transport must be implemented before deployment.

Endpoint behavior may change as the project develops.