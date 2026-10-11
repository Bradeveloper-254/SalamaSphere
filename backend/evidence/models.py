import uuid

from django.db import models


class Evidence(models.Model):
    class EvidenceType(models.TextChoices):
        AUDIO = "audio", "Audio"
        IMAGE = "image", "Image"
        VIDEO = "video", "Video"
        DOCUMENT = "document", "Document"
        OTHER = "other", "Other"

    class VerificationStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        VERIFIED = "verified", "Verified"
        MISMATCH = "mismatch", "Mismatch"
        FAILED = "failed", "Failed"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    incident = models.ForeignKey(
        "incidents.Incident",
        on_delete=models.PROTECT,
        related_name="evidence_files",
    )

    evidence_type = models.CharField(
        max_length=20,
        choices=EvidenceType.choices,
    )

    original_filename = models.CharField(
        max_length=255,
    )

    storage_key = models.CharField(
        max_length=500,
        unique=True,
    )

    mime_type = models.CharField(
        max_length=100,
        blank=True,
    )

    file_size_bytes = models.PositiveBigIntegerField()

    sha256_hash = models.CharField(
        max_length=64,
        blank=True,
    )

    verification_status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING,
    )

    recorded_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    uploaded_at = models.DateTimeField(
        auto_now_add=True,
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    def __str__(self):
        return self.original_filename