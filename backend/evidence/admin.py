from django.contrib import admin

from .models import Evidence, EvidenceAccessAudit


@admin.register(Evidence)
class EvidenceAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "incident",
        "evidence_type",
        "original_filename",
        "encryption_version",
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
        "encryption_version",
        "uploaded_at",
    )


@admin.register(EvidenceAccessAudit)
class EvidenceAccessAuditAdmin(admin.ModelAdmin):
    list_display = ("occurred_at", "incident", "evidence", "user", "action", "outcome")
    list_filter = ("action", "outcome")
    readonly_fields = tuple(field.name for field in EvidenceAccessAudit._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
