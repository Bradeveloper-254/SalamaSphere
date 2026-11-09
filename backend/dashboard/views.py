from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.contrib import messages
from django.shortcuts import redirect

from .audit import record_incident_audit
from .forms import IncidentReviewNoteForm
from .models import IncidentAuditEvent, IncidentReviewNote
from accounts.models import User
from emergency_notifications.models import EmergencyNotification
from incidents.models import Incident, IncidentAssignment
from notifications.models import Notification
from notifications.services import create_system_notification
from notifications.services import get_administrators, notify_case_assigned

from .audit import record_incident_audit
from .models import IncidentAuditEvent

def authorized_incidents_for(user):
    """
    Return incidents the current user is allowed to access.

    Survivors see their own incidents.
    Administrators may see incidents for administrative review.
    Other roles receive no incident access until explicit sharing
    or assignment permissions have been implemented.
    """
    if not user.is_authenticated:
        return Incident.objects.none()

    if user.role == User.Role.SURVIVOR:
        return Incident.objects.filter(
            user=user,
        ).select_related(
            "user",
            "device",
        ).prefetch_related(
            "evidence_files",
        )

    if user.is_active and (
        user.is_superuser
        or (user.role == User.Role.ADMIN and user.is_staff)
    ):
        return Incident.objects.all().select_related(
            "user",
            "device",
        ).prefetch_related(
            "evidence_files",
        )

    return Incident.objects.none()


@login_required
def incident_dashboard(request):
    incidents = authorized_incidents_for(
        request.user
    ).order_by("-received_at")

    summary = incidents.aggregate(
        total=Count("id"),
        high_priority=Count(
            "id",
            filter=Q(threat_level="high"),
        ),
        pending=Count(
            "id",
            filter=Q(status="pending"),
        ),
    )

    recent_incidents = incidents[:10]

    return render(
        request,
        "dashboard/incidents.html",
        {
            "summary": summary,
            "incidents": recent_incidents,
            "unread_notification_count": Notification.objects.filter(
                recipient=request.user,
                is_read=False,
            ).count(),
        },
    )


@login_required
def incident_detail(request, incident_id):
    incident = authorized_incidents_for(
        request.user
    ).filter(
        id=incident_id,
    ).first()

    if incident is None:
        # Do not reveal whether another user's incident exists.
        raise Http404("Incident not found.")

    evidence_files = incident.evidence_files.all()

    audio_files = evidence_files.filter(
        evidence_type="audio",
    )
    notification_history = (
        EmergencyNotification.objects
        .filter(incident=incident)
        .select_related("recipient")
        .order_by("-created_at")
    )
    review_notes = incident.review_notes.select_related(
        "author"
    ).all()

    can_write_review_note = (
        request.user.is_authenticated
        and request.user.is_active
        and (
            request.user.is_superuser
            or (
                request.user.is_staff
                and request.user.role == User.Role.ADMIN
            )
        )
    )
    active_assignment = incident.authority_assignments.filter(
        is_active=True,
    ).select_related("authority").first()
    assignable_authorities = User.objects.none()
    if can_write_review_note and active_assignment is None:
        assignable_authorities = User.objects.filter(
            role=User.Role.AUTHORITY,
            authority_status=User.AuthorityStatus.APPROVED,
            is_active=True,
            is_available=True,
        ).exclude(
            assigned_incident_cases__is_active=True,
        ).order_by("username")

    record_incident_audit(
    actor=request.user,
    incident=incident,
    action=IncidentAuditEvent.Action.INCIDENT_VIEWED,
    outcome=IncidentAuditEvent.Outcome.SUCCESS,
    )

    return render(
        request,
        "dashboard/incident_detail.html",
        {
            "incident": incident,
            "evidence_files": evidence_files,
            "audio_files": audio_files,
            "notification_history": notification_history,
            "review_notes": review_notes,
            "can_write_review_note": can_write_review_note,
            "active_assignment": active_assignment,
            "assignable_authorities": assignable_authorities,
            "can_assign_incident": can_write_review_note,
            "unread_notification_count": Notification.objects.filter(
                recipient=request.user,
                is_read=False,
            ).count(),
        },
    )


@login_required
def assign_incident(request, incident_id):
    if not (
        request.user.is_active
        and (
            request.user.is_superuser
            or (
                request.user.is_staff
                and request.user.role == User.Role.ADMIN
            )
        )
    ):
        raise Http404("Incident not found.")

    if request.method != "POST":
        return redirect(
            "dashboard:incident_detail",
            incident_id=incident_id,
        )

    authority_id = request.POST.get("authority_id")
    try:
        with transaction.atomic():
            incident = Incident.objects.select_for_update().filter(
                pk=incident_id,
            ).first()
            if incident is None:
                raise Http404("Incident not found.")
            if (
                incident.status == Incident.IncidentStatus.CLOSED
                or incident.authority_assignments.filter(
                    is_active=True,
                ).exists()
            ):
                messages.error(
                    request,
                    "This incident is closed or already assigned.",
                )
                return redirect(
                    "dashboard:incident_detail",
                    incident_id=incident.id,
                )

            authority = User.objects.select_for_update().filter(
                pk=authority_id,
                role=User.Role.AUTHORITY,
                authority_status=User.AuthorityStatus.APPROVED,
                is_active=True,
                is_available=True,
            ).first()
            if authority is None or authority.assigned_incident_cases.filter(
                is_active=True,
            ).exists():
                messages.error(
                    request,
                    "Choose an active, approved authority who is available.",
                )
                return redirect(
                    "dashboard:incident_detail",
                    incident_id=incident.id,
                )

            assignment = IncidentAssignment.objects.create(
                incident=incident,
                authority=authority,
                assigned_by=request.user,
            )
            authority.is_available = False
            authority.save(update_fields=["is_available"])
            notify_case_assigned(assignment)
    except IntegrityError:
        messages.error(
            request,
            "This incident or authority was assigned in another request. Refresh and try again.",
        )
        return redirect(
            "dashboard:incident_detail",
            incident_id=incident_id,
        )

    messages.success(request, "Incident assigned successfully.")
    return redirect(
        "dashboard:incident_detail",
        incident_id=incident_id,
    )


@login_required
def notification_inbox(request):
    notifications = Notification.objects.filter(
        recipient=request.user,
    ).order_by("-created_at")
    return render(
        request,
        "dashboard/notifications.html",
        {
            "notifications": notifications,
            "unread_notification_count": notifications.filter(
                is_read=False,
            ).count(),
        },
    )


@login_required
def mark_notification_read(request, notification_id):
    if request.method != "POST":
        return redirect("dashboard:notifications")

    notification = get_object_or_404(
        Notification,
        pk=notification_id,
        recipient=request.user,
    )
    notification.is_read = True
    notification.save(update_fields=["is_read"])
    messages.success(request, "Notification marked as read.")
    return redirect("dashboard:notifications")


@login_required
def create_review_note(request, incident_id):
    # Only active staff administrators may create review notes
    # in this first version.
    if not (
        request.user.is_authenticated
        and request.user.is_active
        and (
            request.user.is_superuser
            or (
                request.user.is_staff
                and request.user.role == User.Role.ADMIN
            )
        )
    ):
        raise Http404("Incident not found.")

    incident = Incident.objects.filter(
        id=incident_id
    ).first()

    if incident is None:
        raise Http404("Incident not found.")

    if request.method != "POST":
        return redirect(
            "dashboard:incident_detail",
            incident_id=incident.id,
        )

    form = IncidentReviewNoteForm(request.POST)

    if form.is_valid():
        review_note = form.save(commit=False)
        review_note.incident = incident
        review_note.author = request.user
        review_note.save()

        for administrator in get_administrators():
            create_system_notification(
                recipient=administrator,
                incident=incident,
                title="Incident review note added",
                message=(
                    f"{request.user.get_username()} added a review note "
                    f"to incident {str(incident.pk)[:8].upper()}."
                ),
            )

        record_incident_audit(
            actor=request.user,
            incident=incident,
            action=(
                IncidentAuditEvent.Action.REVIEW_NOTE_CREATED
            ),
            outcome=IncidentAuditEvent.Outcome.SUCCESS,
        )

        messages.success(
            request,
            "Review note saved successfully.",
        )

    else:
        messages.error(
            request,
            "Please correct the review note and try again.",
        )

    return redirect(
        "dashboard:incident_detail",
        incident_id=incident.id,
    )