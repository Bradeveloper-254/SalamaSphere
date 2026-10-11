from django.contrib import admin

from .models import Evidence


@admin.register(Evidence)
class EvidenceAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "incident",
        "evidence_type",
        "original_filename",
        "verification_status",
        "uploaded_at",
    )

    list_filter = (
        "evidence_type",
        "verification_status",
    )

    search_fields = (
        "original_filename",
        "incident__id",
        "sha256_hash",
    )

    readonly_fields = (
        "id",
        "sha256_hash",
        "uploaded_at",
    )