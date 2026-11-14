
import logging
import uuid
from dataclasses import dataclass
from typing import Protocol

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


def get_voice_provider() -> VoiceCallProvider:
    """
    Select the configured voice provider.
    Only mock mode is supported at this stage.
    """

    mode = settings.AT_VOICE_MODE

    if mode == "mock":
        return MockVoiceProvider()

    if mode == "africas_talking":
        raise NotImplementedError(
            "Africa's Talking voice integration has not "
            "been enabled yet."
        )

    raise ValueError(
        f"Unsupported AT_VOICE_MODE: {mode}"
    )
