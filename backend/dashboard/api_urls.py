from django.urls import path

from .api_views import DashboardOverviewView, AdminSettingsOverviewView

urlpatterns = [
    path("overview/", DashboardOverviewView.as_view(), name="dashboard-overview"),
    path("admin/settings/", AdminSettingsOverviewView.as_view(), name="admin-settings-overview"),
]
