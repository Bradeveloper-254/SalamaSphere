from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path(
        "incidents/",
        views.incident_dashboard,
        name="incident_list",
    ),
    path(
        "incidents/<uuid:incident_id>/",
        views.incident_detail,
        name="incident_detail",
    ),
    path(
    "incidents/<uuid:incident_id>/notes/",
    views.create_review_note,
    name="create_review_note",
   ),
]