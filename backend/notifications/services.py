from django.contrib.auth import get_user_model
from django.db import models

from .models import Notification


User = get_user_model()


def create_incident_notification(
    *,
    recipient,
    incident,
    title,
    message,
    notification_type=Notification.NotificationType.INCIDENT,
):
    return Notification.objects.create(
        recipient=recipient,
        incident=incident,
        notification_type=notification_type,
        title=title,
        message=message,
    )


def notify_new_incident(incident):
    create_incident_notification(
        recipient=incident.user,
        incident=incident,
        title="Incident received",
        message="Your incident was received and is awaiting review.",
        notification_type=(
            Notification.NotificationType.SOS
            if incident.is_sos
            else Notification.NotificationType.INCIDENT
        ),
    )
    administrators = User.objects.filter(
        is_active=True,
    ).filter(
        models.Q(is_superuser=True)
        | models.Q(is_staff=True, role=User.Role.ADMIN)
    )
    for administrator in administrators:
        create_incident_notification(
            recipient=administrator,
            incident=incident,
            title="New incident uploaded",
            message=(
                f"A {incident.threat_level} priority incident was submitted "
                "and is awaiting assignment."
            ),
            notification_type=Notification.NotificationType.SOS
            if incident.is_sos
            else Notification.NotificationType.INCIDENT,
        )


def notify_case_assigned(assignment):
    incident = assignment.incident
    create_incident_notification(
        recipient=assignment.authority,
        incident=incident,
        title="Case assigned to you",
        message=(
            f"A {incident.threat_level} priority incident near your "
            "reported location has been assigned to you."
        ),
        notification_type=Notification.NotificationType.SOS
        if incident.is_sos
        else Notification.NotificationType.INCIDENT,
    )
    create_incident_notification(
        recipient=incident.user,
        incident=incident,
        title="Your case has been assigned",
        message="An approved authority has been assigned to your incident.",
    )


def notify_case_resolved(assignment):
    incident = assignment.incident
    recipients = {incident.user, assignment.authority, assignment.assigned_by}
    for recipient in recipients:
        create_incident_notification(
            recipient=recipient,
            incident=incident,
            title="Incident resolved",
            message="The assigned authority marked this incident as resolved.",
        )
