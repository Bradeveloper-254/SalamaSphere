import base64
import json
from dataclasses import dataclass
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import hashlib
from django.conf import settings


@dataclass
class SMSResult:
    accepted: bool
    provider_message_id: str = ""
    provider_status: str = ""
    error: str = ""


class SMSProvider(Protocol):
    def send_sms(
        self,
        phone_number: str,
        message: str,
    ) -> SMSResult:
        ...


class ConsoleSMSProvider:
    """
    Simulated provider for local development.

    Does not send real SMS messages.
    """

    def send_sms(
        self,
        phone_number: str,
        message: str,
    ) -> SMSResult:

        print("\n=== SALAMASPHERE SIMULATED SMS ===")
        print(f"Recipient: {phone_number}")
        print(f"Message:\n{message}")
        print("NO REAL SMS WAS SENT")
        print("=================================\n")

        return SMSResult(
            accepted=True,
            provider_message_id="SIMULATED-TEST",
            provider_status="simulated",
        )


class MobileSasaProvider:
    """Send SMS through the Mobile Sasa API."""

    def send_sms(self, phone_number: str, message: str) -> SMSResult:
        token = settings.MOBILESASA_TOKEN

        if not token:
            return SMSResult(
                accepted=False,
                error="MOBILESASA_TOKEN is not configured.",
            )

        payload = {
            "senderID": settings.MOBILESASA_SENDER_ID,
            "phone": phone_number,
            "message": message,
        }

        request = Request(
            f"{settings.MOBILESASA_BASE_URL.rstrip('/')}/v1/send/message",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )

        try:
            with urlopen(request, timeout=20) as response:
                data = json.loads(response.read().decode("utf-8"))

                accepted = (
                    response.status == 200
                    and data.get("status") is True
                    and data.get("responseCode") == "0200"
                )

                return SMSResult(
                    accepted=accepted,
                    provider_message_id=str(data.get("messageId", "")),
                    provider_status=str(data.get("responseCode", "")),
                    error="" if accepted else str(data.get("message", "Rejected")),
                )

        except HTTPError as error:
            details = error.read().decode("utf-8", errors="replace")
            return SMSResult(
                accepted=False,
                provider_status=str(error.code),
                error=details[:500],
            )

        except (URLError, TimeoutError, OSError) as error:
            return SMSResult(
                accepted=False,
                provider_status="connection_error",
                error=str(error)[:500],
            )

        except (ValueError, json.JSONDecodeError) as error:
            return SMSResult(
                accepted=False,
                provider_status="invalid_response",
                error=str(error)[:500],
            )

class ESMSAfricaProvider:
    """
    Sends SMS through the eSMS Africa HTTP API.
    Uses a stable idempotency key to reduce duplicate sends.
    """

    def send_sms(self, phone_number: str, message: str) -> SMSResult:
        api_key = settings.ESMS_API_KEY

        if not api_key:
            return SMSResult(
                accepted=False,
                error="ESMS_API_KEY is not configured.",
            )

        payload = {
            "to": phone_number,
            "text": message,
        }

        if settings.ESMS_SENDER_ID:
            payload["sender_id"] = settings.ESMS_SENDER_ID

        # Stable for the same recipient and message.
        idempotency_key = hashlib.sha256(
            f"{phone_number}:{message}".encode("utf-8")
        ).hexdigest()

        request = Request(
            f"{settings.ESMS_BASE_URL.rstrip('/')}/api/messages/send",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Idempotency-Key": idempotency_key,
            },
            method="POST",
        )

        try:
            with urlopen(request, timeout=20) as response:
                response_body = response.read().decode("utf-8")
                data = json.loads(response_body) if response_body else {}

                message_id = (
                    data.get("message_id")
                    or data.get("id")
                    or ""
                )
                provider_status = data.get("status", "accepted")

                return SMSResult(
                    accepted=200 <= response.status < 300,
                    provider_message_id=str(message_id),
                    provider_status=str(provider_status),
                )

        except HTTPError as error:
            details = error.read().decode("utf-8", errors="replace")
            return SMSResult(
                accepted=False,
                provider_status=str(error.code),
                error=details[:500] or str(error),
            )

        except (URLError, TimeoutError, OSError) as error:
            return SMSResult(
                accepted=False,
                provider_status="connection_error",
                error=str(error)[:500],
            )

        except (ValueError, json.JSONDecodeError) as error:
            return SMSResult(
                accepted=False,
                provider_status="invalid_response",
                error=str(error)[:500],
            )

class TwilioSMSProvider:
    """Send SMS messages through Twilio's Messages REST API."""

    def send_sms(self, phone_number: str, message: str) -> SMSResult:
        account_sid = settings.TWILIO_ACCOUNT_SID
        auth_token = settings.TWILIO_AUTH_TOKEN
        messaging_service_sid = settings.TWILIO_MESSAGING_SERVICE_SID
        from_number = settings.TWILIO_FROM_NUMBER

        if not account_sid or not auth_token:
            return SMSResult(
                accepted=False,
                provider_status="not_configured",
                error="Twilio account SID and auth token are required.",
            )
        if not messaging_service_sid and not from_number:
            return SMSResult(
                accepted=False,
                provider_status="not_configured",
                error=(
                    "Configure a Twilio messaging service SID "
                    "or sender phone number."
                ),
            )

        fields = {"To": phone_number, "Body": message}
        if messaging_service_sid:
            fields["MessagingServiceSid"] = messaging_service_sid
        else:
            fields["From"] = from_number

        credentials = base64.b64encode(
            f"{account_sid}:{auth_token}".encode("utf-8")
        ).decode("ascii")
        request = Request(
            (
                "https://api.twilio.com/2010-04-01/Accounts/"
                f"{account_sid}/Messages.json"
            ),
            data=urlencode(fields).encode("utf-8"),
            headers={
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
            method="POST",
        )

        try:
            with urlopen(request, timeout=10) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            try:
                payload = json.loads(error.read().decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                payload = {}
            return SMSResult(
                accepted=False,
                provider_status=str(error.code),
                error=str(payload.get("message") or "Twilio rejected the SMS."),
            )
        except (URLError, TimeoutError, OSError):
            raise

        return SMSResult(
            accepted=True,
            provider_message_id=str(payload.get("sid") or ""),
            provider_status=str(payload.get("status") or "accepted"),
        )


def get_sms_provider() -> SMSProvider:
    """Return the configured SMS provider."""
    providers = {
        "console": ConsoleSMSProvider,
        "mobile_sasa": MobileSasaProvider,
        "esms_africa": ESMSAfricaProvider,
        "twilio": TwilioSMSProvider,
    }
    provider_name = settings.SMS_PROVIDER
    try:
        provider_class = providers[provider_name]
    except KeyError as error:
        supported = ", ".join(sorted(providers))
        raise ValueError(
            f"Unsupported SMS_PROVIDER {provider_name!r}; "
            f"choose one of: {supported}."
        ) from error
    return provider_class()
