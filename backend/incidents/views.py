
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone
from math import asin, cos, radians, sin, sqrt

from rest_framework import generics, status
from rest_framework.exceptions import APIException
from rest_framework.permissions import (
    BasePermission,
    IsAuthenticated,
)
from rest_framework.response import Response
from rest_framework.views import APIView

from devices.models import WearableDevice
from dashboard.audit import record_incident_audit
from dashboard.models import IncidentAuditEvent
from emergency_notifications.services import queue_emergency_notifications
from emergency_notifications.tasks import enqueue_incident_notifications
from emergency_notifications.voice_services import queue_voice_notifications
from notifications.services import (
    notify_case_assigned,
    notify_case_resolved,
    notify_new_incident,
)

from .models import Incident, IncidentAssignment
from .serializers import (
    AuthorityIncidentSerializer,
    IncidentAssignmentCreateSerializer,
    IncidentSerializer,
)
from threat_analysis.models import ThreatAssessment
from threat_analysis.services import assess_incident

User = get_user_model()


def is_incident_admin(user):
    return user.is_superuser or (
        user.is_active
        and user.is_staff
        and user.role == User.Role.ADMIN
    )


class IncidentListCreateView(generics.ListCreateAPIView):
    serializer_class = IncidentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if is_incident_admin(user):
            return Incident.objects.prefetch_related(
                "evidence_files",
            ).all().order_by("-created_at")

        return Incident.objects.filter(
            Q(device__owner=user)
            | Q(user=user)
        ).prefetch_related(
            "evidence_files",
        ).distinct().order_by("-created_at")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        device_identifier = serializer.validated_data.get(
            "device_identifier"
        )

        if (
            not device_identifier
            and serializer.validated_data.get("source")
            == Incident.IncidentSource.WEARABLE
        ):
            return Response(
                {"device_identifier": "This field is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        device = None
        if device_identifier:
            try:
                device = WearableDevice.objects.get(
                    device_identifier=device_identifier,
                    owner=request.user,
                    status=WearableDevice.DeviceStatus.ACTIVE,
                )
            except WearableDevice.DoesNotExist:
                return Response(
                    {
                        "detail": (
                            "The device was not found, does not belong "
                            "to your account, or is not active."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        event_id = serializer.validated_data.get("client_event_id")

        if event_id is not None:
            existing = Incident.objects.filter(
                user=request.user,
                client_event_id=event_id,
            ).first()

            if existing is not None:
                return Response(
                    self.get_serializer(existing).data,
                    status=status.HTTP_200_OK,
                )

        try:
            with transaction.atomic():
                if device is not None:
                    device.last_seen_at = timezone.now()
                    device.save(update_fields=["last_seen_at", "updated_at"])
                incident = serializer.save(
                    user=request.user,
                    device=device,
                )
                assessment = assess_incident(
                    user_selected_level=incident.threat_level,
                    description=incident.description,
                )
                if assessment["level"] is not None:
                    incident.threat_level = assessment["level"]
                    incident.save(update_fields=["threat_level", "updated_at"])
                ThreatAssessment.objects.create(
                    incident=incident,
                    assessed_by=request.user,
                    suggested_level=assessment["suggested_level"],
                    final_level=assessment["level"],
                    assessment_source=assessment["source"],
                    assessment_reason=assessment["reason"],
                    indicators={
                        "keyword_matches": assessment["keyword_matches"],
                    },
                    needs_review=assessment["needs_review"],
                )
                record_incident_audit(
                    actor=request.user,
                    incident=incident,
                    action=IncidentAuditEvent.Action.INCIDENT_CREATED,
                    outcome=IncidentAuditEvent.Outcome.SUCCESS,
                )
                queued_notifications = queue_emergency_notifications(incident)
                queued_voice_notifications = queue_voice_notifications(
                    incident
                )
                if queued_notifications or queued_voice_notifications:
                    transaction.on_commit(
                        lambda incident_id=incident.pk:
                            enqueue_incident_notifications.delay(
                                str(incident_id)
                            ),
                        robust=True,
                    )
                notify_new_incident(incident)

        except IntegrityError:
            if event_id is not None:
                existing = Incident.objects.filter(
                    user=request.user,
                    client_event_id=event_id,
                ).first()

                if existing is not None:
                    return Response(
                        self.get_serializer(existing).data,
                        status=status.HTTP_200_OK,
                    )

            raise APIException(
                "The incident could not be saved. Please retry."
            )

        return Response(
            self.get_serializer(incident).data,
            status=status.HTTP_201_CREATED,
        )


class IncidentDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = IncidentSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "id"

    def get_queryset(self):
        user = self.request.user
        if is_incident_admin(user):
            return Incident.objects.all()

        return Incident.objects.filter(
            Q(device__owner=user)
            | Q(user=user)
        ).distinct()

    def update(self, request, *args, **kwargs):
        if is_incident_admin(request.user):
            return Response(
                {
                    "detail": (
                        "Administrators cannot edit survivor incidents "
                        "through this endpoint."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        protected_fields = {
            "device_identifier": (
                "The device association cannot be changed "
                "through incident updates."
            ),
            "client_event_id": (
                "The client event identifier cannot be changed."
            ),
            "is_sos": (
                "The SOS status cannot be changed after "
                "incident creation."
            ),
        }

        for field, message in protected_fields.items():
            if field in request.data:
                return Response(
                    {"detail": message},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        return super().update(request, *args, **kwargs)


class IsApprovedAuthority(BasePermission):
    message = "An approved authority account is required."

    def has_permission(self, request, view):
        user = request.user

        return bool(
            user
            and user.is_authenticated
            and user.is_active
            and getattr(user, "role", None) == "authority"
            and getattr(user, "authority_status", None) == "approved"
        )


class AuthorityAssignedIncidentListView(generics.ListAPIView):
    serializer_class = AuthorityIncidentSerializer
    permission_classes = [IsAuthenticated, IsApprovedAuthority]

    def get_queryset(self):
        return (
            Incident.objects.filter(
                authority_assignments__authority=self.request.user,
                authority_assignments__is_active=True,
            )
            .select_related("user", "device")
            .prefetch_related("evidence_files")
            .distinct()
            .order_by("-received_at")
        )


class AuthorityPresenceView(APIView):
    permission_classes = [IsAuthenticated, IsApprovedAuthority]

    def post(self, request):
        latitude = request.data.get("latitude")
        longitude = request.data.get("longitude")
        available = request.data.get("is_available")
        if not isinstance(available, bool):
            return Response(
                {"is_available": ["A boolean value is required."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if available and (latitude is None or longitude is None):
            return Response(
                {"location": ["Location is required when becoming available."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            latitude = float(latitude) if latitude is not None else None
            longitude = float(longitude) if longitude is not None else None
        except (TypeError, ValueError):
            return Response(
                {"location": ["Latitude and longitude must be numbers."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if (
            latitude is not None
            and not -90 <= latitude <= 90
            or longitude is not None
            and not -180 <= longitude <= 180
        ):
            return Response(
                {"location": ["Location coordinates are out of range."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if request.user.assigned_incident_cases.filter(is_active=True).exists():
            return Response(
                {"is_available": ["Resolve your active case before changing availability."]},
                status=status.HTTP_409_CONFLICT,
            )

        request.user.is_available = available
        if latitude is not None and longitude is not None:
            request.user.last_known_latitude = latitude
            request.user.last_known_longitude = longitude
            request.user.location_updated_at = timezone.now()
        request.user.save(update_fields=[
            "is_available",
            "last_known_latitude",
            "last_known_longitude",
            "location_updated_at",
        ])
        return Response({
            "is_available": request.user.is_available,
            "location_updated_at": request.user.location_updated_at,
        })


class IsSalamaSphereAdmin(BasePermission):
    message = "Authorized administrator access is required."

    def has_permission(self, request, view):
        user = request.user

        return bool(
            user
            and user.is_authenticated
            and user.is_active
            and (
                user.is_superuser
                or (
                    user.is_staff
                    and user.role == "admin"
                )
            )
        )


class AdminIncidentAssignmentCreateView(APIView):
    permission_classes = [IsAuthenticated, IsSalamaSphereAdmin]

    def get(self, request):
        incidents = Incident.objects.exclude(
            status=Incident.IncidentStatus.CLOSED,
        ).exclude(
            authority_assignments__is_active=True,
        ).order_by("-received_at")
        return Response([
            {
                "id": str(incident.id),
                "description": incident.description,
                "threat_level": incident.threat_level,
                "status": incident.status,
                "is_sos": incident.is_sos,
                "occurred_at": incident.occurred_at,
                "received_at": incident.received_at,
                "latitude": incident.latitude,
                "longitude": incident.longitude,
                "location_map_url": incident.location_map_url,
                "audio_available": incident.evidence_files.filter(
                    evidence_type="audio",
                ).exists(),
            }
            for incident in incidents
        ])

    @transaction.atomic
    def post(self, request):
        serializer = IncidentAssignmentCreateSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        assignment = serializer.save()

        return Response(
            {
                "message": "Incident assignment saved.",
                "incident_id": str(assignment.incident_id),
                "authority_id": assignment.authority_id,
                "is_active": assignment.is_active,
            },
            status=status.HTTP_200_OK,
        )


class AdminAssignableAuthorityListView(APIView):
    permission_classes = [IsAuthenticated, IsSalamaSphereAdmin]

    def get(self, request):
        incident_id = request.query_params.get("incident_id")
        incident = Incident.objects.filter(pk=incident_id).first()
        if incident is None:
            return Response(
                {"detail": "Incident not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        busy_authority_ids = IncidentAssignment.objects.filter(
            is_active=True,
        ).values_list("authority_id", flat=True)
        authorities = User.objects.filter(
            role=User.Role.AUTHORITY,
            authority_status=User.AuthorityStatus.APPROVED,
            is_active=True,
            is_available=True,
        ).exclude(id__in=busy_authority_ids)

        has_incident_location = (
            incident.latitude is not None
            and incident.longitude is not None
        )
        if has_incident_location:
            authorities = authorities.filter(
                last_known_latitude__isnull=False,
                last_known_longitude__isnull=False,
                location_updated_at__gte=timezone.now() - timedelta(hours=24),
            )

        candidates = []
        incident_lat = (
            radians(float(incident.latitude))
            if has_incident_location
            else None
        )
        incident_lon = (
            radians(float(incident.longitude))
            if has_incident_location
            else None
        )
        for authority in authorities:
            distance_km = None
            if has_incident_location:
                authority_lat = radians(float(authority.last_known_latitude))
                authority_lon = radians(float(authority.last_known_longitude))
                lat_delta = authority_lat - incident_lat
                lon_delta = authority_lon - incident_lon
                haversine = (
                    sin(lat_delta / 2) ** 2
                    + cos(incident_lat)
                    * cos(authority_lat)
                    * sin(lon_delta / 2) ** 2
                )
                distance_km = 6371 * 2 * asin(sqrt(haversine))

            if distance_km is None or distance_km <= 100:
                candidates.append({
                    "id": authority.id,
                    "username": authority.username,
                    "phone_number": authority.phone_number,
                    "latitude": authority.last_known_latitude,
                    "longitude": authority.last_known_longitude,
                    "distance_km": (
                        round(distance_km, 1)
                        if distance_km is not None
                        else None
                    ),
                    "location_updated_at": authority.location_updated_at,
                })
        candidates.sort(
            key=lambda authority: (
                authority["distance_km"] is None,
                authority["distance_km"] or 0,
            )
        )
        return Response(candidates)


class ResolveAssignedIncidentView(APIView):
    permission_classes = [IsAuthenticated, IsApprovedAuthority]

    @transaction.atomic
    def post(self, request, incident_id):
        incident = Incident.objects.select_for_update().filter(
            pk=incident_id,
            authority_assignments__authority=request.user,
            authority_assignments__is_active=True,
        ).first()
        if incident is None:
            return Response(
                {"detail": "No active assigned case was found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        assignment = IncidentAssignment.objects.select_for_update().get(
            incident=incident,
            authority=request.user,
            is_active=True,
        )
        incident.status = Incident.IncidentStatus.CLOSED
        incident.save(update_fields=["status", "updated_at"])
        assignment.is_active = False
        assignment.save(update_fields=["is_active", "updated_at"])
        request.user.is_available = False
        request.user.save(update_fields=["is_available"])
        notify_case_resolved(assignment)
        return Response({
            "incident_id": str(incident.id),
            "status": incident.status,
            "message": "Case marked as resolved.",
        })
