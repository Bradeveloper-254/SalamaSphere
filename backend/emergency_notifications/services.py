from django.db import transaction
from django.utils import timezone

from incidents.models import Incident
from trusted_contacts.models import TrustedContact

from .models import EmergencyNotification
from .providers import ConsoleSMSProvider
from .message_builder import build_emergency_message


@transaction.atomic
def queue_emergency_notifications(incident):
    """
    Queue notifications for an explicitly identified SOS incident.

    This function does not send messages.
    """

    if not isinstance(incident, Incident):
        raise TypeError("A valid Incident instance is required.")

    if not incident.is_sos:
        return []

    if incident.source != Incident.IncidentSource.WEARABLE:
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
    """
    Process one pending notification using a simulated provider
    unless another provider is explicitly supplied.

    This is a development implementation, not a production
    background-worker or delivery-confirmation system.
    """

    provider = provider or ConsoleSMSProvider()

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
            or notification.incident.source
            != Incident.IncidentSource.WEARABLE
        ):
            notification.status = EmergencyNotification.Status.FAILED
            notification.last_error = "Incident is not a valid SOS event."
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

    message = build_emergency_message(notification.incident)

    try:
        result = provider.send_sms(
            notification.recipient.phone_number,
            message,
        )
    except Exception:
        # A timeout may mean a provider accepted the message but
        # the response was lost. Do not automatically retry an
        # ambiguous outcome without provider idempotency support.
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