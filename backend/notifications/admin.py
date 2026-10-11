from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "recipient",
        "notification_type",
        "delivery_status",
        "created_at",
    )

    list_filter = (
        "notification_type",
        "delivery_status",
    )

    search_fields = (
        "title",
        "recipient__username",
        "provider_reference",
    )