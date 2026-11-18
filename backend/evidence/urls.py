
from django.urls import path

from .views import (
    EmergencyIncidentAudioLinkView,
    EmergencyIncidentLinkView,
    EvidenceAudioView,
    EvidenceFileView,
    EvidenceUploadView,
    EvidenceVerificationView,
    EvidenceTranscriptionView,
    EvidenceTranscriptListView,
    EvidenceTranscriptReviewView,
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
        "evidence/<uuid:evidence_id>/transcribe/",
        EvidenceTranscriptionView.as_view(),
        name="evidence-transcribe",
    ),
    path("evidence/<uuid:evidence_id>/transcripts/", EvidenceTranscriptListView.as_view(), name="evidence-transcripts"),
    path("transcripts/<int:transcript_id>/review/", EvidenceTranscriptReviewView.as_view(), name="evidence-transcript-review"),
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
