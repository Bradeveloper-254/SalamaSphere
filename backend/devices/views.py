from django.db import IntegrityError, transaction
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import WearableDevice
from .serializers import DeviceRegistrationSerializer


class DeviceRegistrationView(generics.CreateAPIView):
    serializer_class = DeviceRegistrationSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        device_identifier = request.data.get("device_identifier")
        if isinstance(device_identifier, str):
            existing = WearableDevice.objects.filter(
                device_identifier=device_identifier,
            ).first()
            if existing is not None:
                return self._existing_device_response(existing)

        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except ValidationError:
            existing = WearableDevice.objects.filter(
                device_identifier=device_identifier,
            ).first()
            if existing is None:
                raise
            return self._existing_device_response(existing)
        device_identifier = serializer.validated_data["device_identifier"]

        try:
            with transaction.atomic():
                device = serializer.save(owner=request.user)
        except IntegrityError:
            existing = WearableDevice.objects.filter(
                device_identifier=device_identifier,
            ).first()
            if existing is None:
                raise
            return self._existing_device_response(existing)

        return Response(
            self.get_serializer(device).data,
            status=status.HTTP_201_CREATED,
        )

    def _existing_device_response(self, device):
        if (
            device.owner_id == self.request.user.pk
            and device.status == WearableDevice.DeviceStatus.ACTIVE
        ):
            return Response(
                self.get_serializer(device).data,
                status=status.HTTP_200_OK,
            )

        return Response(
            {
                "detail": (
                    "This wearable is already registered and cannot be "
                    "claimed by this account."
                )
            },
            status=status.HTTP_409_CONFLICT,
        )
