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
    is_sos = models.BooleanField(
        default=False,
        help_text="Whether this incident represents an explicit SOS activation.",
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

    location_captured_at = models.DateTimeField(null=True, blank=True)

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

    @property
    def location_map_url(self):
        if self.latitude is None or self.longitude is None:
            return None
        return (
            "https://www.google.com/maps/search/?api=1&query="
            f"{self.latitude},{self.longitude}"
        )

    def __str__(self):
        return f"{self.id} - {self.threat_level}"
    
    
    


class IncidentLocation(models.Model):
    """Append-only location samples for an active SOS incident."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    incident = models.ForeignKey(
        Incident,
        on_delete=models.PROTECT,
        related_name="location_history",
    )
    client_location_id = models.UUIDField()
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    accuracy_m = models.FloatField(null=True, blank=True)
    captured_at = models.DateTimeField()
    speed_mps = models.FloatField(null=True, blank=True)
    bearing_degrees = models.FloatField(null=True, blank=True)
    source = models.CharField(max_length=30, default="phone_gps")
    received_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-captured_at", "-received_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["incident", "client_location_id"],
                name="unique_incident_client_location",
            ),
        ]
        indexes = [
            models.Index(
                fields=["incident", "-captured_at"],
                name="incident_loc_time_idx",
            ),
        ]

    def __str__(self):
        return f"{self.incident_id} @ {self.captured_at.isoformat()}"


class LiveAudioSession(models.Model):
    """Short-lived, incident-scoped signalling session; media is never stored."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACTIVE = "active", "Active"
        TERMINATED = "terminated", "Terminated"
        EXPIRED = "expired", "Expired"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    incident = models.ForeignKey(Incident, on_delete=models.PROTECT, related_name="live_audio_sessions")
    victim = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="live_audio_sessions")
    responder = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="responder_live_audio_sessions")
    victim_consent = models.BooleanField(default=False)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    expires_at = models.DateTimeField()
    terminated_at = models.DateTimeField(null=True, blank=True)
    victim_token_hash = models.CharField(max_length=64)
    responder_token_hash = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["incident", "status", "expires_at"])]

    @property
    def is_expired(self):
        from django.utils import timezone
        return self.expires_at <= timezone.now()


class LiveAudioSignal(models.Model):
    """Small SDP/ICE signalling messages. Audio data must never be placed here."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(LiveAudioSession, on_delete=models.CASCADE, related_name="signals")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    sequence = models.PositiveIntegerField()
    kind = models.CharField(max_length=16)
    payload = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["session", "sender", "sequence"], name="unique_live_audio_signal_sequence")]
        ordering = ["created_at"]


class IncidentAssignment(models.Model):
    """
    Explicitly links an incident to an authority account.
    Access must still be checked by the API.
    """

    incident = models.ForeignKey(
        Incident,
        on_delete=models.PROTECT,
        related_name="authority_assignments",
    )

    authority = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="assigned_incident_cases",
    )

    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_incident_assignments",
    )

    is_active = models.BooleanField(default=True)

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["incident", "authority"],
                name="unique_incident_authority_assignment",
            ),
            models.UniqueConstraint(
                fields=["incident"],
                condition=models.Q(is_active=True),
                name="unique_active_incident_assignment",
            ),
            models.UniqueConstraint(
                fields=["authority"],
                condition=models.Q(is_active=True),
                name="unique_active_authority_assignment",
            ),
        ]

    def __str__(self):
        return f"{self.incident_id} assigned to {self.authority_id}"
