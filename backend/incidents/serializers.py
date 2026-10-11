from rest_framework import serializers

from devices.models import WearableDevice
from .models import Incident


class IncidentSerializer(serializers.ModelSerializer):
    device_identifier = serializers.CharField(
        write_only=True,
        required=False,
    )
    client_event_id = serializers.UUIDField(
        required=True,
        allow_null=False,
    )

    class Meta:
        model = Incident
        fields = [
            "id",
            "client_event_id",
            "device_identifier",
            "device",
            "source",
            "threat_level",
            "description",
            "occurred_at",
            "received_at",
            "latitude",
            "longitude",
            "location_accuracy_m",
            "location_source",
            "status",
            "sync_received_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "device",
            "received_at",
            "sync_received_at",
            "created_at",
            "updated_at",
        ]

    def validate_device_identifier(self, value):
        request = self.context.get("request")

        if request is None or not request.user.is_authenticated:
            raise serializers.ValidationError(
                "Authentication is required."
            )

        device = WearableDevice.objects.filter(
            device_identifier=value,
            owner=request.user,
            status=WearableDevice.DeviceStatus.ACTIVE,
        ).first()

        if device is None:
            raise serializers.ValidationError(
                "Device not found, inactive, revoked, or not assigned to you."
            )

        return value



    def validate_threat_level(self, value):
        allowed_levels = {"low", "medium", "high"}

        if value not in allowed_levels:
            raise serializers.ValidationError(
                "Threat level must be low, medium, or high."
            )

        return value

    def validate(self, attrs):
        latitude = attrs.get("latitude")
        longitude = attrs.get("longitude")

        if (latitude is None) != (longitude is None):
            raise serializers.ValidationError({
                "location": (
                    "Latitude and longitude must either both be "
                    "provided or both be omitted."
                )
            })

        return attrs

    def create(self, validated_data):
        device_identifier = validated_data.pop("device_identifier")
        request = self.context["request"]

        device = WearableDevice.objects.get(
            device_identifier=device_identifier,
            owner=request.user,
            status=WearableDevice.DeviceStatus.ACTIVE,
        )

        return Incident.objects.create(
            device=device,
            user=request.user,
            **validated_data,
        )
        
    def validate_latitude(self, value):
        if value is not None and not -90 <= value <= 90:
            raise serializers.ValidationError(
                "Latitude must be between -90 and 90."
            )
        return value


    def validate_longitude(self, value):
        if value is not None and not -180 <= value <= 180:
            raise serializers.ValidationError(
                "Longitude must be between -180 and 180."
            )
        return value