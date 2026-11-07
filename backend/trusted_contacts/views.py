from django.db.models.deletion import ProtectedError

from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from .models import TrustedContact
from .serializers import TrustedContactSerializer


class TrustedContactListCreateView(generics.ListCreateAPIView):
    serializer_class = TrustedContactSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return TrustedContact.objects.filter(
            user=self.request.user,
            is_active=True,
        ).order_by("-created_at")


class TrustedContactDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = TrustedContactSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return TrustedContact.objects.filter(
            user=self.request.user,
            is_active=True,
        )

    def perform_destroy(self, instance):
        try:
            instance.delete()
        except ProtectedError:
            instance.is_active = False
            instance.save(update_fields=["is_active", "updated_at"])
