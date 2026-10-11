from django.contrib import admin

from .models import WearableDevice


@admin.register(WearableDevice)
class WearableDeviceAdmin(admin.ModelAdmin):
    list_display = (
        "device_name",
        "owner",
        "status",
        "last_seen_at",
        "created_at",
    )

    list_filter = (
        "status",
    )

    search_fields = (
        "device_name",
        "device_identifier",
        "owner__username",
    )