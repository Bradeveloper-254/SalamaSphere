from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from incidents.models import Incident
from dashboard.audit import record_incident_audit
from dashboard.models import IncidentAuditEvent

from .models import ThreatAssessment
from .serializers import (
    ThreatAssessmentCreateSerializer,
    ThreatAssessmentReviewSerializer,
)
from .services import assess_incident


def user_can_access_incident(user, incident):
    if not user.is_authenticated or not user.is_active:
        return False

    if incident.user_id == user.pk or (
        incident.device_id
        and incident.device.owner_id == user.pk
    ):
        return True

    if user.is_superuser or (
        user.is_staff and getattr(user, "role", None) == "admin"
    ):
        return True

    return bool(
        getattr(user, "role", None) == "authority"
        and getattr(user, "authority_status", None) == "approved"
        and incident.authority_assignments.filter(
            authority=user,
            is_active=True,
        ).exists()
    )


def get_authorized_incident(user, incident_id):
    incident = get_object_or_404(
        Incident.objects.select_related("device"),
        pk=incident_id,
    )

    if not user_can_access_incident(user, incident):
        record_incident_audit(
            actor=user,
            incident=incident,
            action=IncidentAuditEvent.Action.ACCESS_DENIED,
            outcome=IncidentAuditEvent.Outcome.FAILURE,
        )
        return None

    return incident


class ThreatAssessmentCreateView(APIView):

    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, incident_id):

        serializer = ThreatAssessmentCreateSerializer(
            data=request.data
        )

        serializer.is_valid(raise_exception=True)

        incident = get_authorized_incident(
            request.user,
            incident_id,
        )

        if incident is None:
            return Response(
                {"detail": "Incident not found or inaccessible."},
                status=status.HTTP_404_NOT_FOUND,
            )

        data = serializer.validated_data

        selected_level = data.get("user_selected_level")
        indicators = data.get("indicators", {})
        explanation = data.get("user_explanation", "")

        try:
            result = assess_incident(
                user_selected_level=selected_level,
                indicators=indicators,
                description=incident.description,
            )
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        assessment = ThreatAssessment.objects.create(
            incident=incident,
            assessed_by=request.user,
            suggested_level=result["suggested_level"],
            final_level=result["level"],
            assessment_source=result["source"],
            assessment_reason=result["reason"],
            indicators={
                **indicators,
                "keyword_matches": result["keyword_matches"],
            },
            user_explanation=explanation,
            needs_review=result["needs_review"],
        )
        if result["level"] is not None:
            incident.threat_level = result["level"]
            incident.save(update_fields=["threat_level", "updated_at"])
        record_incident_audit(
            actor=request.user,
            incident=incident,
            action=IncidentAuditEvent.Action.THREAT_ASSESSMENT_CREATED,
            outcome=IncidentAuditEvent.Outcome.SUCCESS,
        )

        return Response(
            {
                "id": str(assessment.id),
                "incident_id": str(incident.pk),
                "suggested_level": assessment.suggested_level,
                "final_level": assessment.final_level,
                "assessment_source": assessment.assessment_source,
                "assessment_reason": assessment.assessment_reason,
                "needs_review": assessment.needs_review,
                "review_status": assessment.review_status,
                "created_at": assessment.created_at,
            },
            status=status.HTTP_201_CREATED,
        )


class ThreatAssessmentReviewView(APIView):

    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, assessment_id):

        serializer = ThreatAssessmentReviewSerializer(
            data=request.data
        )

        serializer.is_valid(raise_exception=True)

        assessment = get_object_or_404(
            ThreatAssessment.objects.select_related(
                "incident",
                "assessed_by",
            ),
            pk=assessment_id,
        )

        if not user_can_access_incident(
            request.user,
            assessment.incident,
        ):
            return Response(
                {"detail": "Assessment not found or inaccessible."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Only the original assessor may review this assessment
        # in this initial implementation.
        if assessment.assessed_by_id != request.user.id:
            record_incident_audit(
                actor=request.user,
                incident=assessment.incident,
                action=IncidentAuditEvent.Action.ACCESS_DENIED,
                outcome=IncidentAuditEvent.Outcome.FAILURE,
            )
            return Response(
                {
                    "detail": (
                        "Only the user who created this assessment "
                        "may review it."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        data = serializer.validated_data

        action = data["action"]
        explanation = data.get("explanation", "")

        if action == "accept":
            assessment.review_status = "accepted"

            if assessment.final_level is None:
                return Response(
                    {
                        "detail": (
                            "Select a threat level before accepting "
                            "an assessment without a classification."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        elif action == "correct":
            assessment.final_level = data["corrected_level"]
            assessment.review_status = "corrected"

        elif action == "mark_incorrect":
            assessment.review_status = "marked_incorrect"

            # Do not silently erase the original suggestion.
            # A survivor can optionally provide a replacement level.
            if data.get("corrected_level"):
                assessment.final_level = data["corrected_level"]

        assessment.user_explanation = explanation
        assessment.needs_review = False
        assessment.reviewed_at = timezone.now()
        assessment.reviewed_by = request.user

        assessment.save(
            update_fields=[
                "final_level",
                "review_status",
                "user_explanation",
                "needs_review",
                "reviewed_at",
                "reviewed_by",
            ]
        )
        if assessment.final_level is not None:
            incident = assessment.incident
            incident.threat_level = assessment.final_level
            incident.save(update_fields=["threat_level", "updated_at"])
        record_incident_audit(
            actor=request.user,
            incident=assessment.incident,
            action=IncidentAuditEvent.Action.THREAT_ASSESSMENT_REVIEWED,
            outcome=IncidentAuditEvent.Outcome.SUCCESS,
        )

        return Response(
            {
                "id": str(assessment.id),
                "suggested_level": assessment.suggested_level,
                "final_level": assessment.final_level,
                "review_status": assessment.review_status,
                "user_explanation": assessment.user_explanation,
                "needs_review": assessment.needs_review,
                "reviewed_at": assessment.reviewed_at,
            },
            status=status.HTTP_200_OK,
        )