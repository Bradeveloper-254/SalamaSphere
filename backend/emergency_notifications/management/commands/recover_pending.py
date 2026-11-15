from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from emergency_notifications.models import EmergencyNotification
from emergency_notifications.services import process_emergency_notification
from emergency_notifications.voice_services import process_voice_notification


class Command(BaseCommand):
    help = (
        "Mark stale notification attempts UNKNOWN and process a bounded "
        "batch of PENDING notifications. UNKNOWN calls are never redialed."
    )

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=100)
        parser.add_argument("--stale-minutes", type=int, default=10)

    def handle(self, *args, **options):
        limit = options["limit"]
        stale_minutes = options["stale_minutes"]
        if limit < 1 or stale_minutes < 1:
            raise CommandError("--limit and --stale-minutes must be positive.")

        stale_before = timezone.now() - timedelta(minutes=stale_minutes)
        with transaction.atomic():
            stale_count = EmergencyNotification.objects.filter(
                status=EmergencyNotification.Status.PROCESSING,
                updated_at__lt=stale_before,
            ).update(
                status=EmergencyNotification.Status.UNKNOWN,
                provider_status="unknown",
                last_error=(
                    "Processing timed out; provider outcome is unknown. "
                    "Automatic retry was suppressed."
                ),
                updated_at=timezone.now(),
            )

        pending_ids = list(
            EmergencyNotification.objects.filter(
                status=EmergencyNotification.Status.PENDING,
            )
            .order_by("created_at")
            .values_list("pk", "channel")[:limit]
        )
        for notification_id, channel in pending_ids:
            if channel == "voice":
                notification = process_voice_notification(notification_id)
            elif channel == "sms":
                notification = process_emergency_notification(notification_id)
            else:
                self.stderr.write(
                    f"Skipping unsupported channel on {notification_id}."
                )
                continue
            self.stdout.write(
                f"{notification_id} {channel} {notification.status}"
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Marked {stale_count} stale attempts UNKNOWN; "
                f"processed {len(pending_ids)} pending notifications."
            )
        )
