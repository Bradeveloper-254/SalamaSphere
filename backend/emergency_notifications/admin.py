from django.contrib import admin

from .models import EmergencyNotification


@admin.register(EmergencyNotification)
class EmergencyNotificationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "incident_id",
        "recipient_id",
        "channel",
        "status",
        "provider_status",
        "attempt_count",
        "updated_at",
    )
    list_filter = ("channel", "status", "provider_status")
    search_fields = (
        "id",
        "incident_id",
        "recipient_id",
        "provider_message_id",
        "provider_request_id",
    )
    readonly_fields = tuple(field.name for field in EmergencyNotification._meta.fields)
