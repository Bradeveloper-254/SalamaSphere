from django.urls import path

from .views import LoginView, RegistrationView,CurrentUserView
from .approval_views import (
    AuthorityAccountStatusView,
    PendingAuthorityApplicationsView,
    ApproveAuthorityView,
    RejectAuthorityView,
    AuthorityAccountManagementView,
AuthorityAccountStatusView,
)
from .document_views import AuthorityVerificationDocumentUploadView
from .document_review_views import (
    AuthorityVerificationDocumentListView,
    AuthorityVerificationDocumentDetailView,
    AuthorityVerificationDocumentDownloadView,
)
urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("register/", RegistrationView.as_view(), name="register"),

    path(
        "authority-applications/",
        PendingAuthorityApplicationsView.as_view(),
        name="pending-authorities",
    ),

    path(
        "authority-applications/<int:user_id>/approve/",
        ApproveAuthorityView.as_view(),
        name="approve-authority",
    ),
    path("me/", CurrentUserView.as_view(), name="current-user"),
    path(
        "authority-applications/<int:user_id>/reject/",
        RejectAuthorityView.as_view(),
        name="reject-authority",
    ),
    path(
    "verification-documents/",
    AuthorityVerificationDocumentUploadView.as_view(),
    name="authority-verification-document-upload",
   ),
    path(
    "admin/verification-documents/",
    AuthorityVerificationDocumentListView.as_view(),
    name="admin-verification-documents",
),

path(
    "admin/verification-documents/<int:document_id>/",
    AuthorityVerificationDocumentDetailView.as_view(),
    name="admin-verification-document-detail",
),

path(
    "admin/verification-documents/<int:document_id>/download/",
    AuthorityVerificationDocumentDownloadView.as_view(),
    name="admin-verification-document-download",
),
path(
    "admin/authorities/",
    AuthorityAccountManagementView.as_view(),
    name="admin-authority-accounts",
),
path(
    "admin/authorities/<int:user_id>/status/",
    AuthorityAccountStatusView.as_view(),
    name="admin-authority-account-status",
),
]