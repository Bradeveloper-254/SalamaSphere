
from django.urls import path
from .views import (
    AdminAssignableAuthorityListView,
    AdminIncidentAssignmentCreateView,
    AuthorityPresenceView,
    ResolveAssignedIncidentView,
)
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
        "authority/presence/",
        AuthorityPresenceView.as_view(),
        name="authority-presence",
    ),
    path(
        "authority/assigned/<uuid:incident_id>/resolve/",
        ResolveAssignedIncidentView.as_view(),
        name="authority-resolve-incident",
    ),
    path(
        "admin/unassigned/",
        AdminIncidentAssignmentCreateView.as_view(),
        name="admin-unassigned-incidents",
    ),
    path(
        "admin/assignments/available-authorities/",
        AdminAssignableAuthorityListView.as_view(),
        name="admin-assignable-authorities",
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
