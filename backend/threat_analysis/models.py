import uuid

from django.conf import settings
from django.db import models


class ThreatAssessment(models.Model):
    class ThreatLevel(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"

    class AssessmentSource(models.TextChoices):
        USER = "user", "User Selected"
        RULES = "rules", "Rule Based"
        NLP = "nlp", "NLP Model"
        REVIEW = "review", "Human Review"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    incident = models.ForeignKey(
        "incidents.Incident",
        on_delete=models.CASCADE,
        related_name="threat_assessments",
    )

    threat_level = models.CharField(
        max_length=10,
        choices=ThreatLevel.choices,
    )

    assessment_source = models.CharField(
        max_length=20,
        choices=AssessmentSource.choices,
        default=AssessmentSource.USER,
    )

    confidence_score = models.FloatField(
        null=True,
        blank=True,
    )

    explanation = models.TextField(
        blank=True,
    )

    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_threat_assessments",
    )

    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    def __str__(self):
        return f"{self.incident_id}: {self.threat_level}"