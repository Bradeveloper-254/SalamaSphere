from urllib.parse import urlsplit

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from emergency_notifications.models import EmergencyNotification


class Command(BaseCommand):
    help = "Read-only notification diagnostics; never sends or retries messages."

    def add_arguments(self, parser):
        parser.add_argument("--incident-id")
        parser.add_argument("--notification-id")
        parser.add_argument("--limit", type=int, default=50)
        parser.add_argument("--config", action="store_true")

    def handle(self, *args, **options):
        if options["config"]:
            self._configuration()
        if options["incident_id"] and options["notification_id"]:
            raise CommandError("Choose incident ID or notification ID, not both.")
        queryset = EmergencyNotification.objects.select_related(
            "incident", "recipient"
        )
        if options["incident_id"]:
            queryset = queryset.filter(incident_id=options["incident_id"])
        if options["notification_id"]:
            queryset = queryset.filter(pk=options["notification_id"])
        limit = options["limit"]
        if limit < 1 or limit > 500:
            raise CommandError("Limit must be between 1 and 500.")
        if not options["incident_id"] and not options["notification_id"]:
            self.stdout.write("Provide --incident-id or --notification-id to inspect records.")
            return
        records = list(queryset.order_by("-created_at")[:limit])
        if not records:
            self.stdout.write("No matching emergency notifications.")
        for item in records:
            self.stdout.write(
                " ".join((
                    f"notification_id={item.pk}",
                    f"incident_id={item.incident_id}",
                    f"contact_id={item.recipient_id}",
                    f"channel={item.channel}",
                    f"status={item.status}",
                    f"provider_status={item.provider_status or 'unknown'}",
                    f"request_id={item.provider_request_id or 'unavailable'}",
                    f"provider_id={item.provider_message_id or 'unavailable'}",
                    f"attempts={item.attempt_count}",
                    f"updated_at={item.updated_at.isoformat()}",
                    f"error_present={bool(item.last_error)}",
                ))
            )

    def _configuration(self):
        self.stdout.write(f"SMS_PROVIDER={settings.SMS_PROVIDER}")
        self.stdout.write(f"MOBILESASA_TOKEN configured={bool(settings.MOBILESASA_TOKEN)}")
        self.stdout.write(f"MOBILESASA_SENDER_ID configured={bool(settings.MOBILESASA_SENDER_ID)}")
        self.stdout.write(f"AT_VOICE_MODE={settings.AT_VOICE_MODE}")
        self.stdout.write(f"AT_VOICE_USERNAME configured={bool(settings.AT_VOICE_USERNAME)}")
        self.stdout.write(f"AT_VOICE_API_KEY configured={bool(settings.AT_VOICE_API_KEY)}")
        self.stdout.write(f"AT_VOICE_NUMBER configured={bool(settings.AT_VOICE_NUMBER)}")
        self.stdout.write(f"AT_VOICE_CALLBACK_TOKEN configured={bool(settings.AT_VOICE_CALLBACK_TOKEN)}")
        for name in ("AT_VOICE_CALLBACK_URL", "AT_VOICE_EVENTS_URL"):
            parsed = urlsplit(getattr(settings, name, ""))
            self.stdout.write(
                f"{name}={parsed.scheme}://{parsed.netloc}{parsed.path} "
                f"configured={bool(parsed.scheme and parsed.netloc)} token_present={'token' in parsed.query}"
            )
