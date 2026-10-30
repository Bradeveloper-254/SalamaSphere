from dataclasses import dataclass
from typing import Protocol


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