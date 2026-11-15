
import logging

from .models import EmergencyNotification
from .services import process_emergency_notification
from .voice_services import process_voice_notification

logger = logging.getLogger(__name__)


def dispatch_incident_notifications(incident_id):
    """
    Process pending SMS and voice notifications directly.

    This implementation does not require a Celery worker.
    It is intended for controlled prototype deployment.
    """

    pending = list(
        EmergencyNotification.objects.filter(
            incident_id=incident_id,
            status=EmergencyNotification.Status.PENDING,
        )
        .order_by("created_at")
        .values_list("id", "channel")
    )

    results = []

    for notification_id, channel in pending:
        try:
            if channel == "sms":
                notification = process_emergency_notification(
                    notification_id
                )
            elif channel == "voice":
                notification = process_voice_notification(
                    notification_id
                )
            else:
                logger.warning(
                    "Unsupported notification channel: %s",
                    channel,
                )
                continue

            results.append({
                "notification_id": str(notification_id),
                "channel": channel,
                "status": notification.status,
            })

            logger.info(
                "SalamaSphere notification processed: "
                "id=%s channel=%s status=%s",
                notification_id,
                channel,
                notification.status,
            )

        except Exception:
            logger.exception(
                "Unexpected error processing notification %s",
                notification_id,
            )

    return results
