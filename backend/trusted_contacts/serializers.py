from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from .models import TrustedContact, VoiceConsentEvent


VOICE_CONSENT_METHOD = "trusted_contact_form"
VOICE_CONSENT_WORDING_VERSION = "voice-consent-v1"


class TrustedContactSerializer(serializers.ModelSerializer):
    confirm_sos_consent = serializers.BooleanField(
        write_only=True,
        required=False,
    )
    confirm_voice_consent = serializers.BooleanField(
        write_only=True,
        required=False,
    )

    class Meta:
        model = TrustedContact
        fields = [
            "id",
            "name",
            "phone_number",
            "relationship",
            "is_active",
            "receive_sos_alerts",
            "receive_voice_calls",
            "voice_consent_confirmed_at",
            "voice_consent_withdrawn_at",
            "voice_consent_method",
            "voice_consent_version",
            "consent_confirmed",
            "consent_confirmed_at",
            "confirm_sos_consent",
            "confirm_voice_consent",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "consent_confirmed",
            "consent_confirmed_at",
            "voice_consent_confirmed_at",
            "voice_consent_withdrawn_at",
            "voice_consent_method",
            "voice_consent_version",
            "created_at",
            "updated_at",
        ]

    def validate_phone_number(self, value):
        value = value.strip().replace(" ", "")

        if not value.startswith("+"):
            raise serializers.ValidationError(
                "Use international phone format, for example +2547XXXXXXXX."
            )

        digits = value[1:]

        if not digits.isdigit() or not 8 <= len(digits) <= 15:
            raise serializers.ValidationError(
                "Enter a valid international phone number."
            )

        return value

    def validate(self, attrs):
        receive_sos_alerts = attrs.get(
            "receive_sos_alerts",
            self.instance.receive_sos_alerts if self.instance else True,
        )
        if (
            self.instance is None
            and receive_sos_alerts
            and attrs.get("confirm_sos_consent") is not True
        ):
            raise serializers.ValidationError({
                "confirm_sos_consent": (
                    "Confirm that the contact agreed to receive SOS alerts."
                )
            })

        receive_voice_calls = attrs.get(
            "receive_voice_calls",
            self.instance.receive_voice_calls if self.instance else False,
        )
        if (
            receive_voice_calls
            and "receive_voice_calls" in attrs
            and attrs.get("confirm_voice_consent") is not True
        ):
            raise serializers.ValidationError({
                "confirm_voice_consent": (
                    "Confirm that the contact agreed to receive "
                    "automated voice calls."
                )
            })
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        consent_confirmed = validated_data.pop(
            "confirm_sos_consent",
            False,
        )
        voice_consent_confirmed = validated_data.pop(
            "confirm_voice_consent",
            False,
        )
        phone_number = validated_data["phone_number"]
        contact = TrustedContact.objects.filter(
            user=self.context["request"].user,
            phone_number=phone_number,
        ).first()
        if contact is not None and contact.is_active:
            raise serializers.ValidationError({
                "phone_number": "This trusted contact already exists."
            })
        if contact is None:
            contact = TrustedContact(user=self.context["request"].user)

        for field, value in validated_data.items():
            setattr(contact, field, value)
        contact.is_active = True
        contact.consent_confirmed = consent_confirmed
        contact.consent_confirmed_at = (
            timezone.now() if consent_confirmed else None
        )
        if contact.receive_voice_calls and voice_consent_confirmed:
            contact.voice_consent_confirmed_at = timezone.now()
            contact.voice_consent_withdrawn_at = None
            contact.voice_consent_method = VOICE_CONSENT_METHOD
            contact.voice_consent_version = VOICE_CONSENT_WORDING_VERSION
        else:
            contact.receive_voice_calls = False
        contact.save()
        if contact.receive_voice_calls:
            VoiceConsentEvent.objects.create(
                contact=contact,
                action=VoiceConsentEvent.Action.GRANTED,
                method=VOICE_CONSENT_METHOD,
                wording_version=VOICE_CONSENT_WORDING_VERSION,
            )
        return contact

    @transaction.atomic
    def update(self, instance, validated_data):
        consent_confirmed = validated_data.pop(
            "confirm_sos_consent",
            None,
        )
        voice_consent_confirmed = validated_data.pop(
            "confirm_voice_consent",
            False,
        )
        previous_voice_consent = instance.receive_voice_calls
        for field, value in validated_data.items():
            setattr(instance, field, value)
        voice_consent_event = None
        if (
            validated_data.get("receive_voice_calls") is True
            and voice_consent_confirmed
        ):
            instance.voice_consent_confirmed_at = timezone.now()
            instance.voice_consent_withdrawn_at = None
            instance.voice_consent_method = VOICE_CONSENT_METHOD
            instance.voice_consent_version = VOICE_CONSENT_WORDING_VERSION
            voice_consent_event = VoiceConsentEvent.Action.GRANTED
        elif (
            validated_data.get("receive_voice_calls") is False
            and previous_voice_consent
        ):
            instance.voice_consent_withdrawn_at = timezone.now()
            voice_consent_event = VoiceConsentEvent.Action.WITHDRAWN
        if consent_confirmed is not None:
            instance.consent_confirmed = consent_confirmed
            instance.consent_confirmed_at = (
                timezone.now() if consent_confirmed else None
            )
        instance.save()
        if voice_consent_event is not None:
            VoiceConsentEvent.objects.create(
                contact=instance,
                action=voice_consent_event,
                method=VOICE_CONSENT_METHOD,
                wording_version=VOICE_CONSENT_WORDING_VERSION,
            )
        return instance