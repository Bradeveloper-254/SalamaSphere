from django.urls import path

from .views import AfricasTalkingVoiceCallbackView

urlpatterns = [
    path(
        "voice/callback/",
        AfricasTalkingVoiceCallbackView.as_view(),
        name="africas-talking-voice-callback",
    ),
]
