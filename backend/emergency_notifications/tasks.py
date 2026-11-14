from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from .models import EmergencyNotification
from .services import process_emergency_notification
from .voice_services import process_voice_notification


@shared_task
def process_notification(notification_id):
    notification = EmergencyNotification.objects.get(pk=notification_id)
    if notification.channel == "voice":
        return process_voice_notification(notification_id).status
    return process_emergency_notification(notification_id).status


@shared_task
def enqueue_incident_notifications(incident_id):
    notification_ids = EmergencyNotification.objects.filter(
        incident_id=incident_id,
        status=EmergencyNotification.Status.PENDING,
    ).values_list("pk", flat=True)
    for notification_id in notification_ids.iterator():
        process_notification.delay(str(notification_id))


@shared_task
def recover_notifications():
    stale_before = timezone.now() - timedelta(
        minutes=settings.EMERGENCY_NOTIFICATION_PROCESSING_TIMEOUT_MINUTES
    )
    EmergencyNotification.objects.filter(
        status=EmergencyNotification.Status.PROCESSING,
        updated_at__lt=stale_before,
    ).update(
        status=EmergencyNotification.Status.UNKNOWN,
        provider_status="unknown",
        last_error=(
            "Processing timed out; provider outcome is unknown. "
            "Automatic redial was suppressed."
        ),
        updated_at=timezone.now(),
    )

    pending_ids = EmergencyNotification.objects.filter(
        status=EmergencyNotification.Status.PENDING,
    ).values_list("pk", flat=True)
    queued = 0
    for notification_id in pending_ids.iterator():
        process_notification.delay(str(notification_id))
        queued += 1
    return queued
