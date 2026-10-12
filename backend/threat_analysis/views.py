from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from incidents.models import Incident

from .models import ThreatAssessment
from .serializers import (
    ThreatAssessmentCreateSerializer,
    ThreatAssessmentReviewSerializer,
)
from .services import assess_incident


def user_can_access_incident(user, incident):
    """
    Replace this function's body with the same authorization
    logic already used by your incident API.

    Do not enable the endpoint with a permissive implementation.
    """

    raise NotImplementedError(
        "Connect this function to the existing incident "
        "authorization logic before enabling this API."
    )


def get_authorized_incident(user, incident_id):
    incident = get_object_or_404(
        Incident,
        pk=incident_id,
    )

    if not user_can_access_incident(user, incident):
        return None

    return incident


class ThreatAssessmentCreateView(APIView):

    permission_classes = [IsAuthenticated]

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
            )
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        assessment = ThreatAssessment.objects.create(
            incident=incident,
            assessed_by=request.user,
            suggested_level=result["level"],
            final_level=result["level"],
            assessment_source=result["source"],
            assessment_reason=result["reason"],
            indicators=indicators,
            user_explanation=explanation,
            needs_review=result["needs_review"],
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

        assessment.save(
            update_fields=[
                "final_level",
                "review_status",
                "user_explanation",
                "needs_review",
                "reviewed_at",
            ]
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