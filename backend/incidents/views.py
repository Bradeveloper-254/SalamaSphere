
from django.db import IntegrityError, transaction

from rest_framework import generics, status
from rest_framework.exceptions import APIException
from rest_framework.permissions import (
    BasePermission,
    IsAuthenticated,
)
from rest_framework.response import Response
from rest_framework.views import APIView

from devices.models import WearableDevice
from emergency_notifications.services import (
    queue_emergency_notifications,
)

from .models import Incident, IncidentAssignment
from .serializers import (
    AuthorityIncidentSerializer,
    IncidentAssignmentCreateSerializer,
    IncidentSerializer,
)


class IncidentListCreateView(generics.ListCreateAPIView):
    serializer_class = IncidentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Incident.objects.filter(
            device__owner=self.request.user
        ).order_by("-created_at")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        device_identifier = serializer.validated_data.get(
            "device_identifier"
        )

        if not device_identifier:
            return Response(
                {"device_identifier": "This field is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

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
                incident = serializer.save(
                    user=request.user,
                    device=device,
                )
                queue_emergency_notifications(incident)

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
        return Incident.objects.filter(
            device__owner=self.request.user
        )

    def update(self, request, *args, **kwargs):
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
            .distinct()
            .order_by("-received_at")
        )



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
