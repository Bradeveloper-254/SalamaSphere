from uuid import UUID

from django.core.management.base import BaseCommand, CommandError

from emergency_notifications.models import EmergencyNotification
from emergency_notifications.services import (
    process_emergency_notification,
)


class Command(BaseCommand):
    help = "Process pending SalamaSphere SOS SMS notifications."

    def add_arguments(self, parser):
        parser.add_argument(
            "--notification-id",
            type=UUID,
            help="Process only this pending notification UUID.",
        )

    def handle(self, *args, **options):
        notification_id = options["notification_id"]
        if notification_id:
            try:
                notification = EmergencyNotification.objects.get(
                    pk=notification_id,
                )
            except EmergencyNotification.DoesNotExist as error:
                raise CommandError(
                    f"Notification {notification_id!r} does not exist."
                ) from error

            result = process_emergency_notification(notification.pk)
            self.stdout.write(f"{result.id}: {result.status}")
            return

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
                "Only pending notifications were considered."
            )
        )