import logging

from django.db import transaction
from django.utils import timezone

from incidents.models import Incident
from trusted_contacts.models import TrustedContact

from .models import EmergencyNotification
from .providers import get_sms_provider
from .message_builder import build_emergency_message

logger = logging.getLogger(__name__)


@transaction.atomic
def queue_emergency_notifications(incident):
    """
    Queue notifications for SOS and wearable incidents.
    """

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
        receive_sos_alerts=True,
        consent_confirmed=True,
    )

    queued = []

    for contact in contacts:
        notification, created = (
            EmergencyNotification.objects.get_or_create(
                incident=incident,
                recipient=contact,
                channel="sms",
                defaults={
                    "status": EmergencyNotification.Status.PENDING,
                },
            )
        )

        if created:
            queued.append(notification)

    return queued


def process_emergency_notification(notification_id, provider=None):
    """Send one queued SOS message through the configured or injected provider."""

    with transaction.atomic():
        notification = (
            EmergencyNotification.objects
            .select_for_update()
            .select_related("incident", "recipient")
            .get(pk=notification_id)
        )

        if notification.status != EmergencyNotification.Status.PENDING:
            return notification

        if (
            not notification.incident.is_sos
            and notification.incident.source
            != Incident.IncidentSource.WEARABLE
        ):
            notification.status = EmergencyNotification.Status.FAILED
            notification.last_error = "Incident is not an eligible SOS event."
            notification.save(
                update_fields=[
                    "status",
                    "last_error",
                    "updated_at",
                ]
            )
            return notification

        contact = notification.recipient

        if (
            not contact.is_active
            or not contact.receive_sos_alerts
            or not contact.consent_confirmed
            or contact.user_id != notification.incident.user_id
        ):
            notification.status = EmergencyNotification.Status.FAILED
            notification.last_error = (
                "Recipient is not eligible for SOS notifications."
            )
            notification.save(
                update_fields=[
                    "status",
                    "last_error",
                    "updated_at",
                ]
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

        # Keep the database lock only while validating and claiming
        # the notification. Provider calls should not run inside
        # this transaction.
        notification_id = notification.pk

    # Fetch the message data outside the transaction.
    notification = (
        EmergencyNotification.objects
        .select_related("incident", "recipient")
        .get(pk=notification_id)
    )

    try:
        provider = provider or get_sms_provider()
        message = build_emergency_message(notification.incident)
        result = provider.send_sms(
            notification.recipient.phone_number,
            message,
        )
    except ValueError as error:
        EmergencyNotification.objects.filter(
            pk=notification_id,
            status=EmergencyNotification.Status.PROCESSING,
        ).update(
            status=EmergencyNotification.Status.FAILED,
            provider_status="not_configured",
            last_error=str(error)[:500],
            updated_at=timezone.now(),
        )
        return EmergencyNotification.objects.get(pk=notification_id)
    except Exception:
        # A timeout may mean a provider accepted the message but
        # the response was lost. Do not automatically retry an
        # ambiguous outcome without provider idempotency support.
        logger.exception(
            "SMS provider outcome is unknown for notification %s",
            notification_id,
        )
        EmergencyNotification.objects.filter(
            pk=notification_id,
            status=EmergencyNotification.Status.PROCESSING,
        ).update(
            status=EmergencyNotification.Status.UNKNOWN,
            provider_status="unknown",
            last_error="Provider outcome is unknown.",
            updated_at=timezone.now(),
        )
        return EmergencyNotification.objects.get(pk=notification_id)

    with transaction.atomic():
        notification = EmergencyNotification.objects.get(
            pk=notification_id
        )

        if result.accepted:
            notification.status = EmergencyNotification.Status.ACCEPTED
            notification.provider_message_id = (
                result.provider_message_id
            )
            notification.provider_status = result.provider_status
            notification.last_error = ""
        else:
            notification.status = EmergencyNotification.Status.FAILED
            notification.provider_status = result.provider_status
            notification.last_error = (
                result.error or "Provider rejected the request."
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


def process_pending_emergency_notifications(incident_id):
    """Send all pending SMS alerts for an incident."""
    pending_ids = list(
        EmergencyNotification.objects.filter(
            incident_id=incident_id,
            status=EmergencyNotification.Status.PENDING,
            channel="sms",
        ).values_list("pk", flat=True)
    )
    return [
        process_emergency_notification(notification_id)
        for notification_id in pending_ids
    ]