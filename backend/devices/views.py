from django.shortcuts import render
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from .models import WearableDevice
from .serializers import DeviceRegistrationSerializer


class DeviceRegistrationView(generics.CreateAPIView):
    serializer_class = DeviceRegistrationSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
