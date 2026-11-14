from django.db import transaction
from django.utils import timezone
from django.db.models.deletion import ProtectedError

from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from .models import TrustedContact, VoiceConsentEvent
from .serializers import (
    VOICE_CONSENT_METHOD,
    VOICE_CONSENT_WORDING_VERSION,
    TrustedContactSerializer,
)


class TrustedContactListCreateView(generics.ListCreateAPIView):
    serializer_class = TrustedContactSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return TrustedContact.objects.filter(
            user=self.request.user,
            is_active=True,
        ).order_by("-created_at")


class TrustedContactDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = TrustedContactSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return TrustedContact.objects.filter(
            user=self.request.user,
            is_active=True,
        )

    @transaction.atomic
    def perform_destroy(self, instance):
        try:
            instance.delete()
        except ProtectedError:
            withdrew_voice_consent = instance.receive_voice_calls
            instance.is_active = False
            instance.receive_voice_calls = False
            update_fields = [
                "is_active",
                "receive_voice_calls",
                "updated_at",
            ]
            if withdrew_voice_consent:
                instance.voice_consent_withdrawn_at = timezone.now()
                update_fields.append("voice_consent_withdrawn_at")
            instance.save(update_fields=update_fields)
            if withdrew_voice_consent:
                VoiceConsentEvent.objects.create(
                    contact=instance,
                    action=VoiceConsentEvent.Action.WITHDRAWN,
                    method=VOICE_CONSENT_METHOD,
                    wording_version=VOICE_CONSENT_WORDING_VERSION,
                )
