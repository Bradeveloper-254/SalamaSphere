from django.db import models

import uuid

from django.conf import settings
from django.db import models


class EmergencyNotification(models.Model):

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        ACCEPTED = "accepted", "Accepted by provider"
        DELIVERED = "delivered", "Delivered"
        FAILED = "failed", "Failed"
        UNKNOWN = "unknown", "Unknown"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    incident = models.ForeignKey(
        "incidents.Incident",
        on_delete=models.PROTECT,
        related_name="emergency_notifications",
    )

    recipient = models.ForeignKey(
        "trusted_contacts.TrustedContact",
        on_delete=models.PROTECT,
        related_name="notifications",
    )

    channel = models.CharField(
        max_length=20,
        default="sms",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    attempt_count = models.PositiveIntegerField(default=0)

    provider_message_id = models.CharField(
        max_length=150,
        blank=True,
    )

    provider_status = models.CharField(
        max_length=50,
        blank=True,
    )

    last_error = models.CharField(
        max_length=500,
        blank=True,
    )

    next_retry_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["status", "next_retry_at"],
                name="emerg_notif_retry_idx",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["incident", "recipient", "channel"],
                name="unique_incident_recipient_channel",
            ),
     ]

    def __str__(self):
        return f"{self.channel} notification {self.id}: {self.status}"