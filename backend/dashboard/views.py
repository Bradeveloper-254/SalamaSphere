from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import render
from django.contrib import messages
from django.shortcuts import redirect

from .audit import record_incident_audit
from .forms import IncidentReviewNoteForm
from .models import IncidentAuditEvent, IncidentReviewNote
from accounts.models import User
from emergency_notifications.models import EmergencyNotification
from incidents.models import Incident

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

    if (
        user.role == User.Role.ADMIN
        and user.is_staff
        and user.is_active
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
        and request.user.is_staff
        and request.user.role == User.Role.ADMIN
    )
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
        },
    )

@login_required
def create_review_note(request, incident_id):
    # Only active staff administrators may create review notes
    # in this first version.
    if not (
        request.user.is_authenticated
        and request.user.is_active
        and request.user.is_staff
        and request.user.role == User.Role.ADMIN
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