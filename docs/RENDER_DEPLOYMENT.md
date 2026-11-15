# SalamaSphere Render deployment notes

The Django web service can dispatch pending SMS and voice notifications after
the incident transaction commits. This direct path does not require Redis, a
Celery worker, or Celery Beat. The request remains open while provider calls
run, so provider latency can make SOS requests slower. A durable worker is the
preferred production setup when one is available.

For a Render web service whose root directory is `backend`, use this start
command:

```text
python -m gunicorn config.wsgi:application
```

Do not append a Celery command to the web command. Configure environment
variables in Render's secret store. In particular, keep `DJANGO_DEBUG` false,
set `DJANGO_ALLOWED_HOSTS` and `DJANGO_CSRF_TRUSTED_ORIGINS` for production
domains, and configure the database and SMS/voice credentials.
Set `EVIDENCE_ENCRYPTION_KEY` to a stable URL-safe base64 encoding of 32 random
bytes and keep it in Render's secret store. Keep the same key across deploys;
changing it makes previously encrypted evidence unreadable. The backend can
derive a key from `DJANGO_SECRET_KEY` when this variable is empty, but that
couples evidence recovery to preserving the Django secret indefinitely.
With `DJANGO_DEBUG=false`, Django's production check currently reports only
the optional HSTS warning. Enable HSTS only after confirming every public
hostname and subdomain is permanently HTTPS; set `SECURE_HSTS_SECONDS` through
deployment configuration once that condition is verified.
`AT_VOICE_CALLBACK_URL` must be the public HTTPS URL
`/api/emergency-notifications/voice/callback/` with the configured callback
token in its query string. Set `AT_VOICE_MODE=africas_talking` only after
configuring a controlled test recipient and the provider's callback URL.

If a service process exits after the database commit but before direct
dispatch, inspect and recover pending records from `backend/` with:

```text
python manage.py recover_pending --limit 100
```

The command processes only `PENDING` records and marks stale `PROCESSING`
records `UNKNOWN`; it never retries an `UNKNOWN` call. Callback events can
still reconcile calls whose provider session was correlated.

The evidence storage setting currently uses Django's local filesystem
storage. Render's free web service has an ephemeral filesystem, so evidence
stored there can disappear on restart or redeploy. Do not rely on it for
preservation. Configure persistent object storage (for example, an S3
compatible service) or a supported persistent disk before storing real
evidence. The current code encrypts evidence before storage, but encryption
does not make ephemeral storage durable.

The free web service can sleep when idle. Its first request after sleeping can
be delayed, and synchronous notification delivery can further delay that
request. This prototype is not a guaranteed emergency-response channel.
