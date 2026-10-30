
from django.urls import path

from .views import (
    EvidenceAudioView,
    EvidenceUploadView,
    EvidenceVerificationView,
)

urlpatterns = [
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
