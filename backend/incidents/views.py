from django.db import IntegrityError, transaction

from rest_framework import generics, status
from rest_framework.exceptions import APIException
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from devices.models import WearableDevice

from .models import Incident
from .serializers import IncidentSerializer


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

    def get_serializer(self, *args, **kwargs):
        # Keep the device association immutable through this endpoint.
        return super().get_serializer(*args, **kwargs)

    def update(self, request, *args, **kwargs):
        if "device_identifier" in request.data:
            return Response(
                {
                    "detail": (
                        "The device association cannot be changed "
                        "through incident updates."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if "client_event_id" in request.data:
            return Response(
                {
                    "detail": (
                        "The client event identifier cannot be changed."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return super().update(request, *args, **kwargs)