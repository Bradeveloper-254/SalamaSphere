
from django.urls import path
from .views import AdminIncidentAssignmentCreateView
from .views import (
    AuthorityAssignedIncidentListView,
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
        "authority/assigned/",
        AuthorityAssignedIncidentListView.as_view(),
        name="authority-assigned-incidents",
    ),
    path(
        "<uuid:id>/",
        IncidentDetailView.as_view(),
        name="incident-detail",
    ),
   path(
    "admin/assignments/",
    AdminIncidentAssignmentCreateView.as_view(),
    name="admin-incident-assignment-create",
), 
]
