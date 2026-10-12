import uuid

from django.conf import settings
from django.db import models


class ThreatAssessment(models.Model):

    LEVEL_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
    ]

    SOURCE_CHOICES = [
        ("rules", "Rules-based assessment"),
        ("user_selected", "Survivor-selected"),
        ("insufficient_information", "Insufficient information"),
    ]

    REVIEW_STATUS_CHOICES = [
        ("pending", "Pending review"),
        ("accepted", "Accepted"),
        ("corrected", "Corrected"),
        ("marked_incorrect", "Marked incorrect"),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    incident = models.ForeignKey(
        "incidents.Incident",
        on_delete=models.PROTECT,
        related_name="threat_assessments",
    )

    assessed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="threat_assessments",
        null=True,
        blank=True,
    )

    suggested_level = models.CharField(
        max_length=10,
        choices=LEVEL_CHOICES,
        null=True,
        blank=True,
    )
    threat_level = models.CharField(
        max_length=10,  
        choices=LEVEL_CHOICES,
        null=True,
        blank=True,
    )

    final_level = models.CharField(
        max_length=10,
        choices=LEVEL_CHOICES,
        null=True,
        blank=True,
    )

    assessment_source = models.CharField(
        max_length=30,
        choices=SOURCE_CHOICES,
    )

    assessment_reason = models.TextField(
        blank=True,
    )

    indicators = models.JSONField(
        default=dict,
        blank=True,
    )

    user_explanation = models.TextField(
        blank=True,
    )

    review_status = models.CharField(
        max_length=20,
        choices=REVIEW_STATUS_CHOICES,
        default="pending",
    )

    needs_review = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="reviewed_threat_assessments",
        null=True,
        blank=True,
    )

    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"Threat assessment for incident {self.incident_id}"
        )