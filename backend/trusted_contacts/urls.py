from django.urls import path

from .views import (
    TrustedContactListCreateView,
    TrustedContactDetailView,
)

urlpatterns = [
    path(
        "",
        TrustedContactListCreateView.as_view(),
        name="trusted-contact-list-create",
    ),
    path(
        "<int:pk>/",
        TrustedContactDetailView.as_view(),
        name="trusted-contact-detail",
    ),
]