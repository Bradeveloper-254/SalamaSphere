import math
import uuid
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from rest_framework import serializers

from devices.models import WearableDevice
from .models import Incident
from django.contrib.auth import get_user_model

from .models import Incident, IncidentAssignment


class CoordinateField(serializers.DecimalField):
    def to_internal_value(self, data):
        try:
            value = Decimal(str(data))
            if value.is_finite() and value.as_tuple().exponent < -self.decimal_places:
                value = value.quantize(
                    Decimal("1").scaleb(-self.decimal_places),
                    rounding=ROUND_HALF_UP,
                )
                data = value
        except (InvalidOperation, TypeError, ValueError):
            pass
        return super().to_internal_value(data)


class IncidentSerializer(serializers.ModelSerializer):
    latitude = CoordinateField(
        max_digits=9,
        decimal_places=6,
        required=False,
        allow_null=True,
    )
    longitude = CoordinateField(
        max_digits=9,
        decimal_places=6,
        required=False,
        allow_null=True,
    )
    location_map_url = serializers.SerializerMethodField()
    audio_available = serializers.SerializerMethodField()
    device_identifier = serializers.CharField(
        write_only=True,
        required=False,
    )
    client_event_id = serializers.UUIDField(
        required=False,
        allow_null=True,
    )
    is_sos = serializers.BooleanField(
        required=False,
        default=False,
    )
    description = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=5000,
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
            "location_map_url",
            "audio_available",
            "location_accuracy_m",
            "location_source",
            "status",
            "sync_received_at",
            "created_at",
            "updated_at",
            "is_sos",
        ]
        read_only_fields = [
            "id",
            "device",
            "received_at",
            "sync_received_at",
            "created_at",
            "updated_at",
            "location_map_url",
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
        device_identifier = validated_data.pop(
            "device_identifier",
            None,
        )
        request = self.context["request"]

        # The view may supply these through serializer.save().
        device = validated_data.pop("device", None)
        user = validated_data.pop("user", request.user)

        # Resolve the device if the view did not supply it.
        if device is None:
            if device_identifier:
                device = WearableDevice.objects.get(
                    device_identifier=device_identifier,
                    owner=request.user,
                    status=WearableDevice.DeviceStatus.ACTIVE,
                )
            elif (
                validated_data.get("source")
                == Incident.IncidentSource.WEARABLE
            ):
                raise serializers.ValidationError({
                    "device_identifier": "This field is required."
                })

        # Enforce ownership using the authenticated user.
        if user != request.user:
            raise serializers.ValidationError(
                "You can only create incidents for yourself."
            )

        # Online clients may not have an offline queue identifier. Keep the
        # field for idempotent sync when supplied, but make ordinary uploads
        # valid by assigning a server-side event id.
        validated_data.setdefault("client_event_id", uuid.uuid4())

        return Incident.objects.create(
            device=device,
            user=request.user,
            **validated_data,
        )


    def validate_longitude(self, value):
        if value is not None and not -180 <= value <= 180:
            raise serializers.ValidationError(
                "Longitude must be between -180 and 180."
            )
        return value

    def validate_latitude(self, value):
        if value is not None and not -90 <= value <= 90:
            raise serializers.ValidationError(
                "Latitude must be between -90 and 90."
            )
        return value

    def validate_location_accuracy_m(self, value):
        if value is not None and (
            not math.isfinite(value) or value < 0
        ):
            raise serializers.ValidationError(
                "Location accuracy must be a finite, non-negative value."
            )
        return value

    def get_location_map_url(self, incident):
        return incident.location_map_url

    def get_audio_available(self, incident):
        return any(
            evidence.evidence_type == "audio"
            for evidence in incident.evidence_files.all()
        )


class AuthorityIncidentSerializer(serializers.ModelSerializer):
    """
    Read-only incident representation for approved authorities
    with an active assignment.
    """

    location_map_url = serializers.SerializerMethodField()
    audio_available = serializers.SerializerMethodField()

    class Meta:
        model = Incident
        fields = [
            "id",
            "source",
            "threat_level",
            "description",
            "occurred_at",
            "received_at",
            "status",
            "is_sos",
            "latitude",
            "longitude",
            "location_map_url",
            "audio_available",
            "location_accuracy_m",
            "location_source",
        ]
        read_only_fields = fields

    def get_location_map_url(self, incident):
        return incident.location_map_url

    def get_audio_available(self, incident):
        return any(
            evidence.evidence_type == "audio"
            for evidence in incident.evidence_files.all()
        )


class IncidentAssignmentCreateSerializer(serializers.Serializer):
    incident_id = serializers.UUIDField()
    authority_id = serializers.IntegerField()
    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=2000,
    )

    def validate(self, attrs):
        incident = Incident.objects.select_for_update().filter(
            pk=attrs["incident_id"],
        ).first()

        if incident is None:
            raise serializers.ValidationError({
                "incident_id": "Incident not found."
            })

        User = get_user_model()

        authority = User.objects.select_for_update().filter(
            pk=attrs["authority_id"],
        ).first()

        if authority is None:
            raise serializers.ValidationError({
                "authority_id": "Authority account not found."
            })

        if (
            not authority.is_active
            or authority.role != "authority"
            or authority.authority_status != "approved"
            or not authority.is_available
        ):
            raise serializers.ValidationError({
                "authority_id": (
                    "Choose an active, approved authority who is available."
                )
            })

        if IncidentAssignment.objects.filter(
            authority=authority,
            is_active=True,
        ).exists():
            raise serializers.ValidationError({
                "authority_id": "This authority is already handling a case."
            })

        if IncidentAssignment.objects.filter(
            incident=incident,
            is_active=True,
        ).exists():
            raise serializers.ValidationError({
                "incident_id": "This incident is already assigned."
            })

        attrs["incident"] = incident
        attrs["authority"] = authority
        return attrs

    def create(self, validated_data):
        incident = validated_data["incident"]
        authority = validated_data["authority"]
        request = self.context["request"]
        notes = validated_data.get("notes", "")

        assignment, created = IncidentAssignment.objects.get_or_create(
            incident=incident,
            authority=authority,
            defaults={
                "assigned_by": request.user,
                "notes": notes,
            },
        )

        if not created and not assignment.is_active:
            assignment.is_active = True
            assignment.assigned_by = request.user
            assignment.notes = notes
            assignment.save(
                update_fields=[
                    "is_active",
                    "assigned_by",
                    "notes",
                    "updated_at",
                ]
            )

        authority.is_available = False
        authority.save(update_fields=["is_available"])

        from notifications.services import notify_case_assigned

        notify_case_assigned(assignment)
        return assignment
