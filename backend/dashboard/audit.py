import logging

from .models import IncidentAuditEvent


logger = logging.getLogger(__name__)


def record_incident_audit(
    *,
    actor,
    action,
    outcome,
    incident=None,
):
    """
    Record an incident-related action.

    Avoid including sensitive evidence contents or unnecessary
    personal information in audit records.
    """
    try:
        return IncidentAuditEvent.objects.create(
            actor=actor,
            incident=incident,
            action=action,
            outcome=outcome,
        )
    except Exception:
        logger.exception(
            "Failed to record an incident audit event."
        )
        raise