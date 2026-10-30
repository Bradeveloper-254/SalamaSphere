from rest_framework import serializers

from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            "id",
            "incident",
            "notification_type",
            "title",
            "message",
            "delivery_status",
            "provider_reference",
            "sent_at",
            "delivered_at",
            "created_at",
        ]
        read_only_fields = fields
