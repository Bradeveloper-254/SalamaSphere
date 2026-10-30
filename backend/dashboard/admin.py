from django.contrib import admin

from .models import (
    IncidentAuditEvent,
    IncidentReviewNote,
)


@admin.register(IncidentReviewNote)
class IncidentReviewNoteAdmin(admin.ModelAdmin):
    list_display = (
        "incident",
        "author",
        "created_at",
    )

    search_fields = (
        "incident__id",
        "author__username",
    )

    readonly_fields = (
        "id",
        "incident",
        "author",
        "note",
        "created_at",
    )


@admin.register(IncidentAuditEvent)
class IncidentAuditEventAdmin(admin.ModelAdmin):
    list_display = (
        "action",
        "outcome",
        "actor",
        "incident",
        "created_at",
    )

    list_filter = (
        "action",
        "outcome",
        "created_at",
    )

    search_fields = (
        "actor__username",
        "incident__id",
    )

    readonly_fields = (
        "id",
        "actor",
        "incident",
        "action",
        "outcome",
        "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False