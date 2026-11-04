from uuid import UUID

from rest_framework import generics
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Notification
from .serializers import NotificationSerializer


class NotificationListView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Notification.objects.filter(
            recipient=self.request.user,
        )
        incident_id = self.request.query_params.get("incident")
        if incident_id is not None:
            try:
                incident_id = UUID(incident_id)
            except ValueError as error:
                raise ValidationError(
                    {"incident": "A valid incident identifier is required."}
                ) from error
            queryset = queryset.filter(incident_id=incident_id)
        return queryset.order_by("-created_at")


class NotificationDetailView(generics.RetrieveAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(
            recipient=self.request.user,
        )

    def patch(self, request, *args, **kwargs):
        notification = self.get_object()
        is_read = request.data.get("is_read")
        if not isinstance(is_read, bool):
            return Response(
                {"is_read": ["A boolean value is required."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        notification.is_read = is_read
        notification.save(update_fields=["is_read"])
        return Response(NotificationSerializer(notification).data)
