from django.shortcuts import render

from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from .models import TrustedContact
from .serializers import TrustedContactSerializer


class TrustedContactListCreateView(generics.ListCreateAPIView):
    serializer_class = TrustedContactSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return TrustedContact.objects.filter(
            user=self.request.user
        ).order_by("-created_at")


class TrustedContactDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = TrustedContactSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return TrustedContact.objects.filter(
            user=self.request.user
        )
