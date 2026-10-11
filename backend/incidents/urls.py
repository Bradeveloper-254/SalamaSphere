from django.urls import path

from .views import (
    IncidentDetailView,
    IncidentListCreateView,
)

urlpatterns = [
    path(
        "",
        IncidentListCreateView.as_view(),
        name="incident-list-create",
    ),
    path(
        "<uuid:id>/",
        IncidentDetailView.as_view(),
        name="incident-detail",
    ),
]