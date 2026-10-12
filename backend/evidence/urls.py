from django.urls import path

from .views import (
    EvidenceUploadView,
    EvidenceVerificationView,
)

urlpatterns = [
    path(
        "incidents/<uuid:incident_id>/",
        EvidenceUploadView.as_view(),
        name="evidence-upload",
    ),
    path(
        "incidents/<uuid:incident_id>/verify/",
        EvidenceVerificationView.as_view(),
        name="evidence-verify",
    ),
]