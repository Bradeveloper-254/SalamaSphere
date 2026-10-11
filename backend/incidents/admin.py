from django.contrib import admin

from .models import Incident


@admin.register(Incident)
class IncidentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "source",
        "threat_level",
        "status",
        "occurred_at",
        "received_at",
    )

    list_filter = (
        "source",
        "threat_level",
        "status",
    )

    search_fields = (
        "id",
        "user__username",
        "description",
    )

    readonly_fields = (
        "id",
        "received_at",
        "created_at",
        "updated_at",
    )