
from datetime import timedelta
from hashlib import sha256
import secrets

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
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from devices.models import WearableDevice
from dashboard.audit import record_incident_audit
from dashboard.models import IncidentAuditEvent
from emergency_notifications.services import queue_emergency_notifications
from emergency_notifications.dispatcher import (
    dispatch_incident_notifications,
)
from emergency_notifications.voice_services import queue_voice_notifications
from notifications.services import (
    notify_case_assigned,
    notify_case_resolved,
    notify_new_incident,
)

from .models import Incident, IncidentAssignment, IncidentLocation, LiveAudioSession, LiveAudioSignal
from .serializers import (
    AuthorityIncidentSerializer,
    IncidentAssignmentCreateSerializer,
    IncidentLocationSerializer,
    IncidentSerializer,
    LiveAudioSessionSerializer,
    LiveAudioSignalSerializer,
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


def _live_audio_incident_for_user(user, incident_id):
    queryset = Incident.objects.filter(pk=incident_id, is_sos=True).select_related("user")
    if is_incident_admin(user):
        return queryset.first()
    return queryset.filter(
        Q(user=user) | Q(authority_assignments__authority=user, authority_assignments__is_active=True)
    ).distinct().first()


def _token_hash(value):
    return sha256(value.encode("utf-8")).hexdigest()


def _is_current_responder(session, user):
    return (
        user == session.responder
        and user.is_active
        and user.role == User.Role.AUTHORITY
        and user.authority_status == "approved"
        and IncidentAssignment.objects.filter(
            incident=session.incident, authority=user, is_active=True
        ).exists()
    )


class LiveAudioSessionView(APIView):
    """Authenticated WebRTC signalling authorization. Never transports audio."""
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "live_audio"

    def post(self, request, incident_id):
        incident = _live_audio_incident_for_user(request.user, incident_id)
        if incident is None or incident.status == Incident.IncidentStatus.CLOSED:
            return Response({"detail": "Active SOS incident not found."}, status=status.HTTP_404_NOT_FOUND)
        if request.user == incident.user:
            return Response({"detail": "Only an assigned responder can create a live-audio session."}, status=status.HTTP_403_FORBIDDEN)
        if not request.user.is_active or request.user.role != User.Role.AUTHORITY or request.user.authority_status != "approved":
            return Response({"detail": "Approved responder authorization is required."}, status=status.HTTP_403_FORBIDDEN)
        # A responder cannot assert survivor consent. The authenticated victim
        # must approve this exact pending session through the approval endpoint.
        session = LiveAudioSession.objects.create(
            incident=incident, victim=incident.user, responder=request.user,
            victim_consent=False, expires_at=timezone.now() + timedelta(minutes=5),
            victim_token_hash=_token_hash(secrets.token_urlsafe(32)),
            responder_token_hash=_token_hash(secrets.token_urlsafe(32)),
        )
        record_incident_audit(actor=request.user, action=IncidentAuditEvent.Action.INCIDENT_VIEWED, outcome=IncidentAuditEvent.Outcome.SUCCESS, incident=incident)
        return Response({"session": LiveAudioSessionSerializer(session).data}, status=status.HTTP_201_CREATED)

    def get(self, request, incident_id):
        incident = _live_audio_incident_for_user(request.user, incident_id)
        if incident is None:
            return Response({"detail": "Incident not found."}, status=status.HTTP_404_NOT_FOUND)
        sessions = LiveAudioSession.objects.filter(incident=incident).exclude(status=LiveAudioSession.Status.EXPIRED)
        return Response(LiveAudioSessionSerializer(sessions, many=True).data)


class LiveAudioApprovalView(APIView):
    """The survivor alone activates a pending session for their incident."""
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "live_audio"

    def post(self, request, session_id):
        session = LiveAudioSession.objects.select_related("incident", "victim", "responder").filter(pk=session_id).first()
        if session is None or request.user != session.victim:
            return Response({"detail": "Pending live-audio request not found."}, status=status.HTTP_404_NOT_FOUND)
        if session.is_expired or session.status != LiveAudioSession.Status.PENDING:
            return Response({"detail": "This approval request has expired or was already used."}, status=status.HTTP_409_CONFLICT)
        if session.incident.status == Incident.IncidentStatus.CLOSED or not _is_current_responder(session, session.responder):
            session.status = LiveAudioSession.Status.TERMINATED
            session.terminated_at = timezone.now()
            session.save(update_fields=["status", "terminated_at"])
            return Response({"detail": "Responder is no longer authorized for this SOS."}, status=status.HTTP_403_FORBIDDEN)
        if request.data.get("approve") is not True:
            session.status = LiveAudioSession.Status.TERMINATED
            session.terminated_at = timezone.now()
            session.save(update_fields=["status", "terminated_at"])
            return Response({"detail": "Live-audio request declined."}, status=status.HTTP_409_CONFLICT)
        session.victim_consent = True
        session.status = LiveAudioSession.Status.ACTIVE
        session.expires_at = timezone.now() + timedelta(minutes=15)
        session.save(update_fields=["victim_consent", "status", "expires_at"])
        record_incident_audit(actor=request.user, action=IncidentAuditEvent.Action.INCIDENT_VIEWED, outcome=IncidentAuditEvent.Outcome.SUCCESS, incident=session.incident)
        return Response({"session": LiveAudioSessionSerializer(session).data})


class LiveAudioSignalView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "live_audio"

    def _session(self, request, session_id):
        session = LiveAudioSession.objects.select_related("incident", "victim", "responder").filter(pk=session_id).first()
        if session is None or request.user not in (session.victim, session.responder):
            return None
        if session.is_expired:
            if session.status != LiveAudioSession.Status.EXPIRED:
                session.status = LiveAudioSession.Status.EXPIRED
                session.save(update_fields=["status"])
            return None
        if (session.incident.status == Incident.IncidentStatus.CLOSED or
                not session.victim_consent or
                session.status != LiveAudioSession.Status.ACTIVE or
                (request.user == session.responder and not _is_current_responder(session, request.user))):
            return None
        return session

    def get(self, request, session_id):
        session = self._session(request, session_id)
        if session is None:
            return Response({"detail": "Live-audio session unavailable."}, status=status.HTTP_404_NOT_FOUND)
        signals = session.signals.exclude(sender=request.user)
        return Response(LiveAudioSignalSerializer(signals, many=True).data)

    def post(self, request, session_id):
        session = self._session(request, session_id)
        if session is None or session.status == LiveAudioSession.Status.TERMINATED:
            return Response({"detail": "Live-audio session unavailable."}, status=status.HTTP_404_NOT_FOUND)
        serializer = LiveAudioSignalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            signal = serializer.save(session=session, sender=request.user)
        except IntegrityError:
            return Response({"detail": "Replayed signal sequence."}, status=status.HTTP_409_CONFLICT)
        if signal.kind == "bye":
            session.status = LiveAudioSession.Status.TERMINATED
            session.terminated_at = timezone.now()
            session.save(update_fields=["status", "terminated_at"])
        elif session.status == LiveAudioSession.Status.PENDING:
            session.status = LiveAudioSession.Status.ACTIVE
            session.save(update_fields=["status"])
        return Response(LiveAudioSignalSerializer(signal).data, status=status.HTTP_201_CREATED)


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
                            dispatch_incident_notifications(incident_id),
                        # Delivery happens inside the web service for the
                        # Render free-plan deployment; Celery remains optional.
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
            "latitude": "Use the incident location endpoint to update GPS.",
            "longitude": "Use the incident location endpoint to update GPS.",
            "location_accuracy_m": "Use the incident location endpoint to update GPS.",
            "location_source": "Use the incident location endpoint to update GPS.",
            "location_captured_at": "Use the incident location endpoint to update GPS.",
        }

        for field, message in protected_fields.items():
            if field in request.data:
                return Response(
                    {"detail": message},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        return super().update(request, *args, **kwargs)


class IncidentLocationView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "incident_location_write"
    latest = False

    def _authorized_incident(self, request, incident_id):
        user = request.user
        queryset = Incident.objects.select_related("user")
        if not is_incident_admin(user):
            queryset = queryset.filter(
                Q(user=user)
                | Q(
                    authority_assignments__authority=user,
                    authority_assignments__is_active=True,
                )
            )
        return queryset.filter(pk=incident_id).first()

    def get(self, request, incident_id, latest=False):
        incident = self._authorized_incident(request, incident_id)
        if incident is None:
            return Response(
                {"detail": "Incident not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        locations = incident.location_history.all()
        if latest:
            location = locations.first()
            stale = (
                location is None
                or location.captured_at < timezone.now() - timedelta(minutes=5)
            )
            return Response({
                "incident_id": str(incident.pk),
                "latest": (
                    IncidentLocationSerializer(location).data
                    if location is not None
                    else None
                ),
                "is_stale": stale,
            })

        before = request.query_params.get("before")
        if before:
            from django.utils.dateparse import parse_datetime

            before_value = parse_datetime(before)
            if before_value is None or timezone.is_naive(before_value):
                return Response(
                    {"before": ["Provide an ISO-8601 timezone-aware timestamp."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            locations = locations.filter(captured_at__lt=before_value)
        try:
            limit = int(request.query_params.get("limit", 100))
        except (TypeError, ValueError):
            return Response(
                {"limit": ["Limit must be an integer."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        limit = min(max(limit, 1), 500)
        page = list(locations.order_by("-captured_at", "-received_at")[:limit + 1])
        has_more = len(page) > limit
        page = page[:limit]
        next_before = page[-1].captured_at.isoformat() if has_more and page else None
        page.sort(key=lambda item: (item.captured_at, item.received_at))
        return Response({
            "incident_id": str(incident.pk),
            "results": IncidentLocationSerializer(page, many=True).data,
            "next_before": next_before,
        })

    def post(self, request, incident_id, latest=False):
        incident = Incident.objects.filter(
            pk=incident_id,
            user=request.user,
        ).first()
        if incident is None:
            return Response(
                {"detail": "Incident not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        if not incident.is_sos or incident.status == Incident.IncidentStatus.CLOSED:
            return Response(
                {"detail": "Location updates require an active SOS incident."},
                status=status.HTTP_409_CONFLICT,
            )

        serializer = IncidentLocationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        client_location_id = serializer.validated_data["client_location_id"]
        existing = IncidentLocation.objects.filter(
            incident=incident,
            client_location_id=client_location_id,
        ).first()
        if existing is not None:
            return Response(
                IncidentLocationSerializer(existing).data,
                status=status.HTTP_200_OK,
            )

        location = serializer.save(incident=incident)
        if (
            incident.location_captured_at is None
            or location.captured_at > incident.location_captured_at
        ):
            incident.latitude = location.latitude
            incident.longitude = location.longitude
            incident.location_accuracy_m = location.accuracy_m
            incident.location_source = location.source
            incident.location_captured_at = location.captured_at
            incident.save(update_fields=[
                "latitude",
                "longitude",
                "location_accuracy_m",
                "location_source",
                "location_captured_at",
                "updated_at",
            ])
        return Response(
            IncidentLocationSerializer(location).data,
            status=status.HTTP_201_CREATED,
        )


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
