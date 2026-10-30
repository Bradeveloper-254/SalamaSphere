import uuid

from rest_framework import serializers

from devices.models import WearableDevice
from .models import Incident
from django.contrib.auth import get_user_model

from .models import Incident, IncidentAssignment

class IncidentSerializer(serializers.ModelSerializer):
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
            "is_sos",
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

        if (
            attrs.get("is_sos", False)
            and attrs.get("source", Incident.IncidentSource.MOBILE)
            != Incident.IncidentSource.WEARABLE
        ):
            raise serializers.ValidationError({
                "is_sos": "SOS incidents must originate from a wearable."
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
            if not device_identifier:
                raise serializers.ValidationError({
                    "device_identifier": "This field is required."
                })

            device = WearableDevice.objects.get(
                device_identifier=device_identifier,
                owner=request.user,
                status=WearableDevice.DeviceStatus.ACTIVE,
            )

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

class AuthorityIncidentSerializer(serializers.ModelSerializer):
    """
    Read-only incident representation for approved authorities
    with an active assignment.
    """

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
            "location_accuracy_m",
            "location_source",
        ]
        read_only_fields = fields


class IncidentAssignmentCreateSerializer(serializers.Serializer):
    incident_id = serializers.UUIDField()
    authority_id = serializers.IntegerField()
    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=2000,
    )

    def validate(self, attrs):
        Incident = __import__(
            "incidents.models",
            fromlist=["Incident"],
        ).Incident

        incident = Incident.objects.filter(
            pk=attrs["incident_id"]
        ).first()

        if incident is None:
            raise serializers.ValidationError({
                "incident_id": "Incident not found."
            })

        User = get_user_model()

        authority = User.objects.filter(
            pk=attrs["authority_id"]
        ).first()

        if authority is None:
            raise serializers.ValidationError({
                "authority_id": "Authority account not found."
            })

        if (
            not authority.is_active
            or authority.role != "authority"
            or authority.authority_status != "approved"
        ):
            raise serializers.ValidationError({
                "authority_id": (
                    "The account must be an active, approved authority."
                )
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

        return assignment
