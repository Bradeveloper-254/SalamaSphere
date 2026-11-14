
import json
import logging
import uuid
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen

from django.conf import settings


logger = logging.getLogger(__name__)


@dataclass
class VoiceCallResult:
    accepted: bool
    provider_call_id: str = ""
    provider_status: str = ""
    error: str = ""


class VoiceCallProvider(Protocol):
    def initiate_call(
        self,
        phone_number: str,
        message: str,
        notification_id: str,
    ) -> VoiceCallResult:
        ...


class VoiceProviderConfigurationError(ValueError):
    pass


class MockVoiceProvider:
    """
    Simulates an outbound emergency call.
    Does not contact or dial any phone number.
    """

    def initiate_call(
        self,
        phone_number: str,
        message: str,
        notification_id: str,
    ) -> VoiceCallResult:

        mock_call_id = f"MOCK-{uuid.uuid4()}"

        logger.info(
            "SALAMASPHERE MOCK VOICE CALL: "
            "notification=%s recipient_suffix=%s call_id=%s",
            notification_id,
            phone_number[-4:],
            mock_call_id,
        )

        print("\n=== SALAMASPHERE SIMULATED VOICE CALL ===")
        print(f"Notification ID: {notification_id}")
        print(f"Recipient ending: ****{phone_number[-4:]}")
        print(f"Simulated call ID: {mock_call_id}")
        print(f"Announcement: {message}")
        print("NO REAL PHONE CALL WAS MADE")
        print("========================================\n")

        return VoiceCallResult(
            accepted=True,
            provider_call_id=mock_call_id,
            provider_status="simulated",
        )


class AfricasTalkingVoiceProvider:
    """Starts an outbound call using Africa's Talking Voice API."""

    def initiate_call(
        self,
        phone_number: str,
        message: str,
        notification_id: str,
    ) -> VoiceCallResult:
        del message
        username = settings.AT_VOICE_USERNAME
        api_key = settings.AT_VOICE_API_KEY
        caller_number = settings.AT_VOICE_NUMBER
        callback_url = settings.AT_VOICE_CALLBACK_URL
        callback_token = settings.AT_VOICE_CALLBACK_TOKEN
        if not all((username, api_key, caller_number)):
            raise VoiceProviderConfigurationError(
                "Africa's Talking voice credentials and caller number "
                "must be configured."
            )
        callback = urlparse(callback_url)
        if (
            callback.scheme != "https"
            or not callback.netloc
            or not callback_token
            or callback_token
            not in parse_qs(callback.query).get("token", [])
        ):
            raise VoiceProviderConfigurationError(
                "Configure an HTTPS Africa's Talking callback URL with "
                "the configured token query parameter."
            )

        payload = urlencode({
            "username": username,
            "from": caller_number,
            "to": phone_number,
        }).encode("utf-8")
        request = Request(
            f"{settings.AT_VOICE_BASE_URL.rstrip('/')}/call",
            data=payload,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
                "apiKey": api_key,
            },
            method="POST",
        )
        with urlopen(request, timeout=10) as response:
            body = response.read()

        try:
            decoded = json.loads(body)
        except (TypeError, UnicodeDecodeError, ValueError) as error:
            raise RuntimeError(
                "Africa's Talking returned an invalid voice API response."
            ) from error

        entries = decoded.get("entries")
        entry = entries[0] if isinstance(entries, list) and entries else {}
        error = str(decoded.get("errorMessage") or "")
        if not entry and not error:
            raise RuntimeError(
                "Africa's Talking returned no call result; outcome is unknown."
            )
        provider_status = str(entry.get("status", ""))
        provider_call_id = str(
            entry.get("sessionId") or entry.get("session_id") or ""
        )
        accepted = provider_status.strip().lower() in {
            "queued",
            "accepted",
            "success",
        }
        if accepted and not provider_call_id:
            logger.warning(
                "Africa's Talking accepted voice notification %s without "
                "returning a session ID; callbacks cannot be correlated.",
                notification_id,
            )
        return VoiceCallResult(
            accepted=accepted,
            provider_call_id=provider_call_id,
            provider_status=provider_status or (
                "rejected" if error else "unknown"
            ),
            error=error or (
                "" if accepted else "Africa's Talking did not queue the call."
            ),
        )


def get_voice_provider() -> VoiceCallProvider:
    """
    Select the configured voice provider.
    Select the mock provider or Africa's Talking Voice API.
    """

    mode = settings.AT_VOICE_MODE

    if mode == "mock":
        return MockVoiceProvider()

    if mode == "africas_talking":
        return AfricasTalkingVoiceProvider()

    raise VoiceProviderConfigurationError(
        f"Unsupported AT_VOICE_MODE: {mode}"
    )
