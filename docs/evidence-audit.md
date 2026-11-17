# Evidence access audit

The evidence audit records authenticated user ID, incident and optional evidence IDs, action, timestamp, outcome, and a caller-supplied request or correlation ID for evidence listing, audio access, downloads, verification, and access denials. Private-link audio requests are attributed to the incident owner because the link identifies an opted-in trusted contact but does not authenticate a Django user.

Audit rows are read-only through Django admin and have no ordinary application API for editing or deletion. The log is stored in the same database as the application and is not tamper-proof: privileged database operators, backups, or compromised application credentials may alter or remove records. Request IDs are accepted from request headers and are correlation hints, not independently verified identities.

Deploy with `python manage.py migrate`. No new environment variables are required.
