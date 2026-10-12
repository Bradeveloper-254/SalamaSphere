from django.urls import path

from .views import (
    ThreatAssessmentCreateView,
    ThreatAssessmentReviewView,
)


urlpatterns = [
    path(
        "incidents/<uuid:incident_id>/threat-assessments/",
        ThreatAssessmentCreateView.as_view(),
        name="threat-assessment-create",
    ),

    path(
        "threat-assessments/<uuid:assessment_id>/review/",
        ThreatAssessmentReviewView.as_view(),
        name="threat-assessment-review",
    ),
]