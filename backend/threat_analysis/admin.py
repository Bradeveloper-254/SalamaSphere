from django.contrib import admin

from .models import ThreatAssessment


@admin.register(ThreatAssessment)
class ThreatAssessmentAdmin(admin.ModelAdmin):
    list_display = (
        "incident",
        "threat_level",
        "assessment_source",
        "reviewed_by",
        "created_at",
    )

    list_filter = (
        "threat_level",
        "assessment_source",
    )

    search_fields = (
        "incident__id",
        "explanation",
    )