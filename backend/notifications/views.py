from uuid import UUID

from django.contrib.auth import get_user_model

from rest_framework import generics
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from incidents.models import IncidentAssignment
from .models import Notification
from .serializers import NotificationSerializer
from .services import (
    create_overdue_case_reminders,
    create_system_notification,
    get_administrators,
)

User = get_user_model()


class NotificationListView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        create_overdue_case_reminders()
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


class AuthorityMessageRecipientsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if (
            request.user.role != User.Role.AUTHORITY
            or request.user.authority_status != User.AuthorityStatus.APPROVED
            or not request.user.is_active
        ):
            return Response(
                {"detail": "Only active, approved authorities can send messages."},
                status=status.HTTP_403_FORBIDDEN,
            )

        admins = get_administrators()
        survivors = User.objects.filter(
            role=User.Role.SURVIVOR,
            incidents__authority_assignments__authority=request.user,
            is_active=True,
        ).distinct()
        recipients = [
            {"id": user.pk, "username": user.get_username(), "role": user.role}
            for user in (*admins, *survivors)
        ]
        return Response(recipients)


class AuthorityMessageCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        authority = request.user
        if (
            authority.role != User.Role.AUTHORITY
            or authority.authority_status != User.AuthorityStatus.APPROVED
            or not authority.is_active
        ):
            return Response(
                {"detail": "Only active, approved authorities can send messages."},
                status=status.HTTP_403_FORBIDDEN,
            )

        recipient_id = request.data.get("recipient_id")
        if isinstance(recipient_id, bool):
            recipient_id = None
        try:
            recipient_id = int(recipient_id)
        except (TypeError, ValueError):
            recipient_id = None

        message = request.data.get("message")
        if not isinstance(message, str) or not message.strip():
            return Response(
                {"message": ["A message is required."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        message = message.strip()
        if len(message) > 5000:
            return Response(
                {"message": ["Messages must be 5000 characters or fewer."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if recipient_id is None:
            return Response(
                {"recipient_id": ["A valid recipient is required."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        recipient = User.objects.filter(pk=recipient_id, is_active=True).first()
        if recipient is None:
            return Response(
                {"recipient_id": ["Recipient not found."]},
                status=status.HTTP_404_NOT_FOUND,
            )

        is_admin = recipient.is_superuser or (
            recipient.is_staff and recipient.role == User.Role.ADMIN
        )
        is_assigned_survivor = (
            recipient.role == User.Role.SURVIVOR
            and IncidentAssignment.objects.filter(
                authority=authority,
                incident__user=recipient,
            ).exists()
        )
        if not (is_admin or is_assigned_survivor):
            return Response(
                {
                    "recipient_id": [
                        "Messages may only be sent to an administrator or a "
                        "survivor with a case assigned to you."
                    ]
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        notification = create_system_notification(
            recipient=recipient,
            title=f"Message from {authority.get_username()}",
            message=message,
        )
        return Response(
            NotificationSerializer(notification).data,
            status=status.HTTP_201_CREATED,
        )
