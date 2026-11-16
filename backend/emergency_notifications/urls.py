from django.urls import path

from .views import (
    AfricasTalkingVoiceControlView,
    AfricasTalkingVoiceEventsView,
)

urlpatterns = [
    path(
        "voice/callback/control/",
        AfricasTalkingVoiceControlView.as_view(),
        name="africas-talking-voice-control",
    ),
    path(
        "voice/callback/events/",
        AfricasTalkingVoiceEventsView.as_view(),
        name="africas-talking-voice-events",
    ),
]
