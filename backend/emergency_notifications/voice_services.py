import logging

from django.db import transaction
from django.utils import timezone

from incidents.models import Incident
from trusted_contacts.models import TrustedContact

from .models import EmergencyNotification
from .voice_provider import (
    VoiceProviderConfigurationError,
    get_voice_provider,
)

logger = logging.getLogger(__name__)


def generate_emergency_voice_announcement(incident, contact=None):
    """Build the spoken emergency announcement for an incident."""
    if not isinstance(incident, Incident):
        raise TypeError("A valid Incident instance is required.")

    announcement = (
        "This is an automated SalamaSphere emergency alert. "
        "A person who listed you as a trusted contact needs help. "
        "Please contact them as soon as possible."
    )
    if (
        incident.location_map_url
        and contact is not None
        and contact.is_active
        and contact.receive_sos_alerts
        and contact.consent_confirmed
    ):
        announcement += (
            " If you receive the consented SMS alert, it includes a map link."
        )
    return announcement


@transaction.atomic
def queue_voice_notifications(incident):
    """Queue one voice notification per opted-in trusted contact."""
    if not isinstance(incident, Incident):
        raise TypeError("A valid Incident instance is required.")

    if (
        not incident.is_sos
        and incident.source != Incident.IncidentSource.WEARABLE
    ):
        return []

    contacts = TrustedContact.objects.filter(
        user=incident.user,
        is_active=True,
        receive_voice_calls=True,
    )

    queued = []
    for contact in contacts:
        notification, created = EmergencyNotification.objects.get_or_create(
            incident=incident,
            recipient=contact,
            channel="voice",
            defaults={"status": EmergencyNotification.Status.PENDING},
        )
        if created:
            queued.append(notification)

    return queued


def process_voice_notification(notification_id, provider=None):
    """Process one queued call using the configured or injected provider."""
    with transaction.atomic():
        notification = (
            EmergencyNotification.objects
            .select_for_update()
            .select_related("incident", "recipient")
            .get(pk=notification_id)
        )

        if notification.status != EmergencyNotification.Status.PENDING:
            return notification

        if notification.channel != "voice":
            notification.status = EmergencyNotification.Status.FAILED
            notification.last_error = "Notification is not a voice call."
            notification.save(
                update_fields=["status", "last_error", "updated_at"]
            )
            return notification

        if (
            not notification.incident.is_sos
            and notification.incident.source
            != Incident.IncidentSource.WEARABLE
        ):
            notification.status = EmergencyNotification.Status.FAILED
            notification.last_error = "Incident is not an eligible SOS event."
            notification.save(
                update_fields=["status", "last_error", "updated_at"]
            )
            return notification

        contact = notification.recipient
        if (
            not contact.is_active
            or not contact.receive_voice_calls
            or contact.user_id != notification.incident.user_id
        ):
            notification.status = EmergencyNotification.Status.FAILED
            notification.last_error = (
                "Recipient has not consented to automated voice calls."
            )
            notification.save(
                update_fields=["status", "last_error", "updated_at"]
            )
            return notification

        notification.status = EmergencyNotification.Status.PROCESSING
        notification.attempt_count += 1
        notification.last_error = ""
        notification.save(
            update_fields=[
                "status",
                "attempt_count",
                "last_error",
                "updated_at",
            ]
        )
        claimed_id = notification.pk

    notification = (
        EmergencyNotification.objects
        .select_related("incident", "recipient")
        .get(pk=claimed_id)
    )

    try:
        provider = provider or get_voice_provider()
        announcement = generate_emergency_voice_announcement(
            notification.incident,
            notification.recipient,
        )
        result = provider.initiate_call(
            notification.recipient.phone_number,
            announcement,
            str(notification.pk),
        )
    except VoiceProviderConfigurationError as error:
        EmergencyNotification.objects.filter(
            pk=claimed_id,
            status=EmergencyNotification.Status.PROCESSING,
        ).update(
            status=EmergencyNotification.Status.FAILED,
            provider_status="not_configured",
            last_error=str(error)[:500],
            updated_at=timezone.now(),
        )
        return EmergencyNotification.objects.get(pk=claimed_id)
    except Exception:
        logger.exception(
            "Voice provider outcome is unknown for notification %s",
            claimed_id,
        )
        EmergencyNotification.objects.filter(
            pk=claimed_id,
            status=EmergencyNotification.Status.PROCESSING,
        ).update(
            status=EmergencyNotification.Status.UNKNOWN,
            provider_status="unknown",
            last_error="Provider outcome is unknown.",
            updated_at=timezone.now(),
        )
        return EmergencyNotification.objects.get(pk=claimed_id)

    with transaction.atomic():
        notification = EmergencyNotification.objects.select_for_update().get(
            pk=claimed_id
        )
        if result.provider_call_id:
            notification.provider_message_id = result.provider_call_id
        if notification.status in {
            EmergencyNotification.Status.PROCESSING,
            EmergencyNotification.Status.UNKNOWN,
        }:
            notification.provider_status = result.provider_status
            if result.accepted:
                notification.status = EmergencyNotification.Status.ACCEPTED
                notification.last_error = ""
            else:
                notification.status = EmergencyNotification.Status.FAILED
                notification.last_error = (
                    result.error or "Provider rejected the call."
                )[:500]
        notification.save(
            update_fields=[
                "status",
                "provider_message_id",
                "provider_status",
                "last_error",
                "updated_at",
            ]
        )

    return notification


def update_voice_call_from_callback(session_id, event_status):
    """Apply a verified provider status callback to its voice notification."""
    status_text = (
        str(event_status or "")
        .strip()
        .lower()
        .replace("_", " ")
        .replace("-", " ")
    )
    status_text = " ".join(status_text.split())
    status_map = {
        "queued": EmergencyNotification.Status.ACCEPTED,
        "accepted": EmergencyNotification.Status.ACCEPTED,
        "ringing": EmergencyNotification.Status.RINGING,
        "answered": EmergencyNotification.Status.ANSWERED,
        "active": EmergencyNotification.Status.ANSWERED,
        "in progress": EmergencyNotification.Status.ANSWERED,
        "completed": EmergencyNotification.Status.COMPLETED,
        "complete": EmergencyNotification.Status.COMPLETED,
        "ended": EmergencyNotification.Status.COMPLETED,
        "failed": EmergencyNotification.Status.FAILED,
        "busy": EmergencyNotification.Status.FAILED,
        "no answer": EmergencyNotification.Status.FAILED,
        "noanswer": EmergencyNotification.Status.FAILED,
        "cancelled": EmergencyNotification.Status.FAILED,
        "canceled": EmergencyNotification.Status.FAILED,
    }
    new_status = status_map.get(status_text)
    if new_status is None:
        raise ValueError("Unsupported Africa's Talking call status.")

    with transaction.atomic():
        notification = (
            EmergencyNotification.objects.select_for_update()
            .select_related("incident", "recipient")
            .filter(
                channel="voice",
                provider_message_id=session_id,
            )
            .first()
        )
        if notification is None:
            return None
        progress = {
            EmergencyNotification.Status.PENDING: 0,
            EmergencyNotification.Status.PROCESSING: 1,
            EmergencyNotification.Status.UNKNOWN: 2,
            EmergencyNotification.Status.ACCEPTED: 3,
            EmergencyNotification.Status.RINGING: 4,
            EmergencyNotification.Status.ANSWERED: 5,
            EmergencyNotification.Status.COMPLETED: 6,
        }
        terminal_statuses = {
            EmergencyNotification.Status.COMPLETED,
            EmergencyNotification.Status.FAILED,
        }
        if notification.status not in terminal_statuses and (
            new_status == EmergencyNotification.Status.FAILED
            or (
                notification.status in progress
                and progress[new_status] > progress[notification.status]
            )
        ):
            notification.status = new_status
            notification.provider_status = status_text[:50]
            notification.last_error = (
                f"Call ended with provider status: {status_text}"[:500]
                if new_status == EmergencyNotification.Status.FAILED
                else ""
            )
            notification.save(
                update_fields=[
                    "status",
                    "provider_status",
                    "last_error",
                    "updated_at",
                ]
            )
        return notification


def process_pending_voice_notifications(incident_id):
    """Process all pending voice calls for an incident."""
    pending_ids = list(
        EmergencyNotification.objects.filter(
            incident_id=incident_id,
            status=EmergencyNotification.Status.PENDING,
            channel="voice",
        ).values_list("pk", flat=True)
    )
    return [
        process_voice_notification(notification_id)
        for notification_id in pending_ids
    ]
