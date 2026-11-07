from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

from .models import Notification


User = get_user_model()


def get_administrators():
    return User.objects.filter(is_active=True).filter(
        models.Q(is_superuser=True)
        | models.Q(is_staff=True, role=User.Role.ADMIN)
    )


def create_system_notification(*, recipient, title, message, incident=None):
    return Notification.objects.create(
        recipient=recipient,
        incident=incident,
        notification_type=Notification.NotificationType.SYSTEM,
        title=title,
        message=message,
    )


def create_system_notification_once(
    *, recipient, title, message, incident=None
):
    existing = Notification.objects.filter(
        recipient=recipient,
        incident=incident,
        notification_type=Notification.NotificationType.SYSTEM,
        title=title,
    ).first()
    if existing is not None:
        return existing, False
    return create_system_notification(
        recipient=recipient,
        title=title,
        message=message,
        incident=incident,
    ), True


def create_overdue_case_reminders():
    from incidents.models import IncidentAssignment

    cutoff = timezone.now() - timedelta(days=14)
    assignments = IncidentAssignment.objects.filter(
        is_active=True,
        created_at__lte=cutoff,
    ).select_related("incident", "authority")
    created_count = 0
    for assignment in assignments.iterator():
        incident = assignment.incident
        reference = str(incident.pk)[:8].upper()
        recipients = {
            assignment.authority,
            *get_administrators(),
        }
        for recipient in recipients:
            _, created = create_system_notification_once(
                recipient=recipient,
                incident=incident,
                title="Case unresolved for 14 days",
                message=(
                    f"Incident {reference} remains assigned to "
                    f"{assignment.authority.get_username()} and has not "
                    "been marked resolved after 14 days."
                ),
            )
            created_count += int(created)
    return created_count


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
    for administrator in get_administrators():
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
    authorities = User.objects.filter(
        role=User.Role.AUTHORITY,
        authority_status=User.AuthorityStatus.APPROVED,
        is_active=True,
    )
    for authority in authorities:
        create_incident_notification(
            recipient=authority,
            incident=incident,
            title="New incident submitted",
            message=(
                f"A {incident.threat_level} priority incident was submitted. "
                "Review available cases and prepare for possible assignment."
            ),
            notification_type=(
                Notification.NotificationType.SOS
                if incident.is_sos
                else Notification.NotificationType.INCIDENT
            ),
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
    for administrator in get_administrators():
        create_incident_notification(
            recipient=administrator,
            incident=incident,
            title="Case assignment completed",
            message=(
                f"Incident {str(incident.pk)[:8].upper()} was assigned to "
                f"{assignment.authority.get_username()}."
            ),
        )


def notify_case_resolved(assignment):
    incident = assignment.incident
    recipients = {
        incident.user,
        assignment.authority,
        assignment.assigned_by,
        *get_administrators(),
    }
    for recipient in recipients:
        create_incident_notification(
            recipient=recipient,
            incident=incident,
            title="Incident resolved",
            message="The assigned authority marked this incident as resolved.",
        )
