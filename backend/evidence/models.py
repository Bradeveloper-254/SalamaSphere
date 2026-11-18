import uuid

from django.conf import settings
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

    uploaded_by = models.ForeignKey(
    settings.AUTH_USER_MODEL,
    on_delete=models.PROTECT,
    related_name="uploaded_evidence",
    null=True,
    blank=True,
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

    sha256_hash_type = models.CharField(max_length=32, default="plaintext")

    encryption_version = models.PositiveSmallIntegerField(
        default=0,
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

    last_verified_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"{self.evidence_type}: {self.original_filename}"


class EvidenceAccessAudit(models.Model):
    class Action(models.TextChoices):
        VIEWED = "viewed", "Evidence viewed"
        AUDIO_ACCESSED = "audio_accessed", "Audio accessed"
        DOWNLOADED = "downloaded", "Evidence downloaded"
        VERIFIED = "verified", "Evidence verification performed"
        ACCESS_DENIED = "access_denied", "Access denied"

    class Outcome(models.TextChoices):
        SUCCESS = "success", "Success"
        DENIED = "denied", "Denied"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    incident = models.ForeignKey("incidents.Incident", on_delete=models.PROTECT)
    evidence = models.ForeignKey(
        Evidence, null=True, blank=True, on_delete=models.PROTECT,
        related_name="access_audit_events",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT,
        related_name="evidence_access_audit_events",
    )
    action = models.CharField(max_length=24, choices=Action.choices)
    occurred_at = models.DateTimeField(auto_now_add=True)
    outcome = models.CharField(max_length=12, choices=Outcome.choices)
    request_id = models.CharField(max_length=128, blank=True)

    class Meta:
        ordering = ["-occurred_at"]


class EvidenceTranscript(models.Model):
    class Status(models.TextChoices):
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    class LanguageSource(models.TextChoices):
        AUTOMATIC = "automatic", "Automatic detection"
        USER_SELECTED = "user_selected", "User selected"

    evidence = models.ForeignKey(
        Evidence, on_delete=models.PROTECT, related_name="transcripts"
    )
    incident = models.ForeignKey(
        "incidents.Incident", on_delete=models.PROTECT,
        related_name="evidence_transcripts",
    )
    language = models.CharField(max_length=16)
    language_source = models.CharField(max_length=20, choices=LanguageSource.choices)
    transcript = models.TextField(blank=True)
    reviewed_transcript = models.TextField(blank=True)
    status = models.CharField(max_length=16, choices=Status.choices)
    error_code = models.CharField(max_length=64, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    human_review_required = models.BooleanField(default=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.PROTECT, related_name="reviewed_evidence_transcripts",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="requested_evidence_transcripts",
    )

    class Meta:
        ordering = ["-processed_at"]


class EvidenceTranscriptRevision(models.Model):
    transcript_record = models.ForeignKey(
        EvidenceTranscript, on_delete=models.PROTECT, related_name="revisions"
    )
    text = models.TextField()
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
