from django.core.management.base import BaseCommand

from emergency_notifications.models import EmergencyNotification
from emergency_notifications.services import (
    process_emergency_notification,
)


class Command(BaseCommand):
    help = "Process pending SalamaSphere SOS notifications using simulation."

    def handle(self, *args, **options):
        pending = EmergencyNotification.objects.filter(
            status=EmergencyNotification.Status.PENDING,
        ).order_by("created_at")

        processed = 0

        for notification in pending.iterator():
            result = process_emergency_notification(notification.pk)

            self.stdout.write(
                f"{result.id}: {result.status}"
            )

            processed += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Processed {processed} notification(s). "
                "The configured default provider is simulated."
            )
        )