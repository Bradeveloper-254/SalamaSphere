from django.db import models

import uuid

from django.conf import settings
from django.db import models


class IncidentReviewNote(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    incident = models.ForeignKey(
        "incidents.Incident",
        on_delete=models.PROTECT,
        related_name="review_notes",
    )

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="incident_review_notes",
    )

    note = models.TextField()

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"Review note for incident {self.incident_id}"
        )
        
class IncidentAuditEvent(models.Model):
    class Action(models.TextChoices):
        INCIDENT_VIEWED = (
            "incident_viewed",
            "Incident viewed",
        )
        EVIDENCE_VERIFICATION = (
            "evidence_verification",
            "Evidence verification",
        )
        REVIEW_NOTE_CREATED = (
            "review_note_created",
            "Review note created",
        )
        ACCESS_DENIED = (
            "access_denied",
            "Access denied",
        )

    class Outcome(models.TextChoices):
        SUCCESS = "success", "Success"
        FAILURE = "failure", "Failure"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="incident_audit_events",
    )

    incident = models.ForeignKey(
        "incidents.Incident",
        on_delete=models.PROTECT,
        related_name="audit_events",
        null=True,
        blank=True,
    )

    action = models.CharField(
        max_length=40,
        choices=Action.choices,
    )

    outcome = models.CharField(
        max_length=20,
        choices=Outcome.choices,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.action} - {self.outcome}"
