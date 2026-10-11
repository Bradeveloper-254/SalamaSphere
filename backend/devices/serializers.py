from rest_framework import serializers

from .models import WearableDevice


class DeviceRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = WearableDevice
        fields = "__all__"

        # The server controls these fields.
        read_only_fields = [
            "id",
            "owner",
            "created_at",
        ]