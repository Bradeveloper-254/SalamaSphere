from django.urls import path

from .views import DeviceRegistrationView

urlpatterns = [
    path(
        "register/",
        DeviceRegistrationView.as_view(),
        name="device-register",
    ),
]