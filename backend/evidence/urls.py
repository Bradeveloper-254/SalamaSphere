
from django.urls import path

from .views import (
    EmergencyIncidentAudioLinkView,
    EmergencyIncidentLinkView,
    EvidenceAudioView,
    EvidenceFileView,
    EvidenceUploadView,
    EvidenceVerificationView,
)

urlpatterns = [
    path(
        "emergency/<str:token>/",
        EmergencyIncidentLinkView.as_view(),
        name="emergency-incident-link",
    ),
    path(
        "emergency/<str:token>/audio/",
        EmergencyIncidentAudioLinkView.as_view(),
        name="emergency-incident-audio",
    ),
    path(
        "evidence/<uuid:evidence_id>/file/",
        EvidenceFileView.as_view(),
        name="evidence-file",
    ),
    path(
        "incidents/<uuid:incident_id>/audio/",
        EvidenceAudioView.as_view(),
        name="incident-audio",
    ),
    path(
        "incidents/<uuid:incident_id>/evidence/",
        EvidenceUploadView.as_view(),
        name="evidence-upload",
    ),
    path(
        "incidents/<uuid:incident_id>/verify/",
        EvidenceVerificationView.as_view(),
        name="evidence-verify",
    ),
]
