from django.core.management.base import BaseCommand
from notifications.services import create_overdue_case_reminders


class Command(BaseCommand):
    help = "Notify authorities and admins about cases unresolved for 14 days."

    def handle(self, *args, **options):
        created_count = create_overdue_case_reminders()
        self.stdout.write(
            self.style.SUCCESS(
                f"Created {created_count} overdue-case reminder(s)."
            )
        )
