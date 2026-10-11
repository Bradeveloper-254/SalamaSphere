import uuid

from django.conf import settings
from django.db import models


class Incident(models.Model):
    class ThreatLevel(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"

    class IncidentSource(models.TextChoices):
        WEARABLE = "wearable", "Wearable"
        MOBILE = "mobile", "Mobile Application"
        WEB = "web", "Web Application"

    class IncidentStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        RECEIVED = "received", "Received"
        REVIEWED = "reviewed", "Reviewed"
        CLOSED = "closed", "Closed"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="incidents",
    )

    device = models.ForeignKey(
        "devices.WearableDevice",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="incidents",
    )

    source = models.CharField(
        max_length=20,
        choices=IncidentSource.choices,
        default=IncidentSource.MOBILE,
    )

    threat_level = models.CharField(
        max_length=10,
        choices=ThreatLevel.choices,
        default=ThreatLevel.MEDIUM,
    )

    description = models.TextField(
        blank=True,
    )

    occurred_at = models.DateTimeField()

    received_at = models.DateTimeField(
        auto_now_add=True,
    )

    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
    )

    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
    )

    location_accuracy_m = models.FloatField(
        null=True,
        blank=True,
    )

    location_source = models.CharField(
        max_length=30,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=IncidentStatus.choices,
        default=IncidentStatus.RECEIVED,
    )

    client_event_id = models.UUIDField(
        null=True,
        blank=True,
        editable=False,
    )

    sync_received_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-received_at"]

        constraints = [
            models.UniqueConstraint(
                fields=["user", "client_event_id"],
                name="unique_user_client_event",
            )
        ]

    def __str__(self):
        return f"{self.id} - {self.threat_level}"