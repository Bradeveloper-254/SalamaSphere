from rest_framework import serializers

from .models import TrustedContact


class TrustedContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrustedContact
        fields = [
            "id",
            "name",
            "phone_number",
            "relationship",
            "is_active",
            "receive_sos_alerts",
            "consent_confirmed",
            "consent_confirmed_at",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "consent_confirmed",
            "consent_confirmed_at",
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

    def create(self, validated_data):
        return TrustedContact.objects.create(
            user=self.context["request"].user,
            **validated_data,
        )