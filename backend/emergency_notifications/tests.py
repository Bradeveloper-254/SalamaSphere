import json
from datetime import timedelta
from io import StringIO
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from django.urls import reverse
from urllib.parse import parse_qs
from rest_framework.test import APIClient

from devices.models import WearableDevice
from evidence.models import Evidence
from incidents.models import Incident
from trusted_contacts.models import TrustedContact

from .models import EmergencyNotification
from .services import (
    queue_emergency_notifications,
    process_emergency_notification,
)
from .providers import ConsoleSMSProvider
from .voice_provider import (
    AfricasTalkingVoiceProvider,
    MockVoiceProvider,
    VoiceCallResult,
)
from .voice_services import (
    generate_emergency_voice_announcement,
    process_voice_notification,
    queue_voice_notifications,
)


User = get_user_model()


class EmergencyNotificationTestBase(TestCase):
    """Shared setup for emergency notification tests."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="salama_test_user",
            password="test-password-only",
        )

        self.device = WearableDevice.objects.create(
            owner=self.user,
            device_name="Test SalamaSphere Wearable",
            device_identifier="SALAMA-TEST-DEVICE-001",
            firmware_version="test-1.0",
            status=WearableDevice.DeviceStatus.ACTIVE,
        )

        self.incident = Incident.objects.create(
            user=self.user,
            device=self.device,
            source=Incident.IncidentSource.WEARABLE,
            threat_level=Incident.ThreatLevel.HIGH,
            description="Development SOS test",
            occurred_at=timezone.now(),
            is_sos=True,
            status=Incident.IncidentStatus.RECEIVED,
        )

        self.contact = TrustedContact.objects.create(
            user=self.user,
            name="Test Trusted Contact",
            phone_number="+254700000000",
            relationship="Test contact",
            is_active=True,
            receive_sos_alerts=True,
            consent_confirmed=True,
            consent_confirmed_at=timezone.now(),
        )

    def create_notification(self, incident=None, contact=None):
        incident = incident or self.incident
        Evidence.objects.get_or_create(
            incident=incident,
            evidence_type=Evidence.EvidenceType.AUDIO,
            defaults={
                "original_filename": "incident.wav",
                "storage_key": f"test-audio/{incident.pk}.wav",
                "file_size_bytes": 4,
                "sha256_hash": "test-hash",
            },
        )
        return EmergencyNotification.objects.create(
            incident=incident,
            recipient=contact or self.contact,
            channel="sms",
            status=EmergencyNotification.Status.PENDING,
        )


class QueueEmergencyNotificationTests(
    EmergencyNotificationTestBase
):
    def test_valid_sos_queues_notification(self):
        queued = queue_emergency_notifications(self.incident)

        self.assertEqual(len(queued), 1)

        self.assertEqual(
            queued[0].status,
            EmergencyNotification.Status.PENDING,
        )

    def test_wearable_incidents_queue_even_without_sos_flag(self):
        self.incident.is_sos = False
        self.incident.save(update_fields=["is_sos"])

        queued = queue_emergency_notifications(self.incident)

        self.assertEqual(len(queued), 1)

    def test_ordinary_mobile_incident_does_not_queue(self):
        self.incident.source = Incident.IncidentSource.MOBILE
        self.incident.is_sos = False
        self.incident.save(update_fields=["source", "is_sos"])

        queued = queue_emergency_notifications(self.incident)

        self.assertEqual(queued, [])

    def test_mobile_sos_queues_notifications(self):
        self.incident.source = Incident.IncidentSource.MOBILE
        self.incident.save(update_fields=["source"])

        queued = queue_emergency_notifications(self.incident)

        self.assertEqual(len(queued), 1)

    def test_sms_matches_emergency_alert_template(self):
        from .message_builder import build_emergency_message

        self.incident.latitude = -1.286389
        self.incident.longitude = 36.817223
        self.incident.save(update_fields=["latitude", "longitude"])
        self.user.first_name = "Amina"
        self.user.last_name = "Wanjiku"
        self.user.save(update_fields=["first_name", "last_name"])

        message = build_emergency_message(self.incident)

        self.assertEqual(
            message,
            "SALAMASPHERE EMERGENCY ALERT\n\n"
            "Amina Wanjiku has triggered an SOS emergency alert.\n\n"
            f"Time: {self.incident.occurred_at.strftime('%d %b %Y, %H:%M UTC')}\n"
            "Location: https://www.google.com/maps/search/?api=1&query="
            "-1.286389,36.817223\n\n"
            "Please try to contact the user and provide assistance.\n\n"
            "This is an automated emergency notification.",
        )

    def test_contact_without_consent_is_not_queued(self):
        self.contact.consent_confirmed = False
        self.contact.save(update_fields=["consent_confirmed"])

        queued = queue_emergency_notifications(self.incident)

        self.assertEqual(queued, [])

    def test_inactive_contact_is_not_queued(self):
        self.contact.is_active = False
        self.contact.save(update_fields=["is_active"])

        queued = queue_emergency_notifications(self.incident)

        self.assertEqual(queued, [])

    def test_contact_who_opted_out_is_not_queued(self):
        self.contact.receive_sos_alerts = False
        self.contact.save(update_fields=["receive_sos_alerts"])

        queued = queue_emergency_notifications(self.incident)

        self.assertEqual(queued, [])

    def test_queueing_same_incident_twice_does_not_duplicate(self):
        first_result = queue_emergency_notifications(
            self.incident
        )

        second_result = queue_emergency_notifications(
            self.incident
        )

        self.assertEqual(len(first_result), 1)
        self.assertEqual(len(second_result), 0)

        self.assertEqual(
            EmergencyNotification.objects.filter(
                incident=self.incident,
                recipient=self.contact,
                channel="sms",
            ).count(),
            1,
        )


class ProcessEmergencyNotificationTests(
    EmergencyNotificationTestBase
):
    def test_provider_accepts_notification(self):
        notification = self.create_notification()

        result = process_emergency_notification(
            notification.pk,
            provider=ConsoleSMSProvider(),
        )

        self.assertEqual(
            result.status,
            EmergencyNotification.Status.ACCEPTED,
        )

        self.assertEqual(
            result.provider_status,
            "simulated",
        )

        self.assertEqual(
            result.provider_message_id,
            "SIMULATED-TEST",
        )

        self.assertEqual(result.attempt_count, 1)

    def test_rejected_notification_is_marked_failed(self):
        notification = self.create_notification()

        fake_provider = Mock()
        fake_provider.send_sms.return_value = Mock(
            accepted=False,
            provider_message_id="",
            provider_status="rejected",
            error="Simulated provider rejection",
        )

        result = process_emergency_notification(
            notification.pk,
            provider=fake_provider,
        )

        self.assertEqual(
            result.status,
            EmergencyNotification.Status.FAILED,
        )

        self.assertEqual(
            result.last_error,
            "Simulated provider rejection",
        )

    def test_provider_exception_marks_result_unknown(self):
        notification = self.create_notification()

        fake_provider = Mock()
        fake_provider.send_sms.side_effect = TimeoutError(
            "Simulated timeout"
        )

        result = process_emergency_notification(
            notification.pk,
            provider=fake_provider,
        )

        self.assertEqual(
            result.status,
            EmergencyNotification.Status.UNKNOWN,
        )

        self.assertEqual(
            result.provider_status,
            "unknown",
        )

    def test_accepted_notification_is_not_sent_again(self):
        notification = self.create_notification()

        fake_provider = Mock()
        fake_provider.send_sms.return_value = Mock(
            accepted=True,
            provider_message_id="SIMULATED-123",
            provider_status="simulated",
            error="",
        )

        first_result = process_emergency_notification(
            notification.pk,
            provider=fake_provider,
        )

        second_result = process_emergency_notification(
            notification.pk,
            provider=fake_provider,
        )

        self.assertEqual(
            first_result.status,
            EmergencyNotification.Status.ACCEPTED,
        )

        self.assertEqual(
            second_result.status,
            EmergencyNotification.Status.ACCEPTED,
        )

        fake_provider.send_sms.assert_called_once()

    def test_ineligible_contact_is_not_sent_a_message(self):
        notification = self.create_notification()

        self.contact.consent_confirmed = False
        self.contact.save(update_fields=["consent_confirmed"])

        fake_provider = Mock()

        result = process_emergency_notification(
            notification.pk,
            provider=fake_provider,
        )

        self.assertEqual(
            result.status,
            EmergencyNotification.Status.FAILED,
        )

        fake_provider.send_sms.assert_not_called()


    def test_wearable_alert_does_not_wait_for_audio_upload(self):
        notification = self.create_notification()
        Evidence.objects.filter(incident=self.incident).delete()
        fake_provider = Mock()
        fake_provider.send_sms.return_value = Mock(
            accepted=True,
            provider_message_id="SM-WEARABLE",
            provider_status="queued",
            error="",
        )

        result = process_emergency_notification(
            notification.pk,
            provider=fake_provider,
        )

        self.assertEqual(result.status, EmergencyNotification.Status.ACCEPTED)
        self.assertEqual(result.attempt_count, 1)
        fake_provider.send_sms.assert_called_once()

    def test_mobile_sos_can_send_without_recorded_audio(self):
        notification = self.create_notification()
        self.incident.source = Incident.IncidentSource.MOBILE
        self.incident.save(update_fields=["source"])
        Evidence.objects.filter(incident=self.incident).delete()
        fake_provider = Mock()
        fake_provider.send_sms.return_value = Mock(
            accepted=True,
            provider_message_id="SM-MOBILE",
            provider_status="queued",
            error="",
        )

        result = process_emergency_notification(
            notification.pk,
            provider=fake_provider,
        )

        self.assertEqual(result.status, EmergencyNotification.Status.ACCEPTED)
        self.assertIn(
            "SALAMASPHERE EMERGENCY ALERT",
            fake_provider.send_sms.call_args.args[1],
        )

    @override_settings(
        TWILIO_ACCOUNT_SID="AC123",
        TWILIO_AUTH_TOKEN="secret-token",
        TWILIO_MESSAGING_SERVICE_SID="MG123",
        TWILIO_FROM_NUMBER="",
    )
    @patch("emergency_notifications.providers.urlopen")
    def test_twilio_provider_sends_configured_message(self, urlopen):
        from .providers import TwilioSMSProvider

        response = Mock()
        response.read.return_value = b'{"sid":"SM123","status":"queued"}'
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        urlopen.return_value = response

        result = TwilioSMSProvider().send_sms(
            "+254700000000",
            "Emergency alert",
        )

        self.assertTrue(result.accepted)
        self.assertEqual(result.provider_message_id, "SM123")
        request = urlopen.call_args.args[0]
        self.assertEqual(request.get_method(), "POST")
        self.assertIn(b"MessagingServiceSid=MG123", request.data)
        self.assertIn(b"To=%2B254700000000", request.data)

    @override_settings(
        MOBILESASA_TOKEN="test-token",
        MOBILESASA_BASE_URL="https://sms.example",
        MOBILESASA_SENDER_ID="SALAMA",
    )
    @patch("emergency_notifications.providers.urlopen")
    def test_mobile_sasa_provider_sends_configured_message(self, urlopen):
        from .providers import MobileSasaProvider

        response = Mock()
        response.status = 200
        response.read.return_value = (
            b'{"status":true,"responseCode":"0200","messageId":"MS123"}'
        )
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        urlopen.return_value = response

        result = MobileSasaProvider().send_sms(
            "+254700000000",
            "Emergency alert",
        )

        self.assertTrue(result.accepted)
        self.assertEqual(result.provider_message_id, "MS123")
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "https://sms.example/v1/send/message")
        self.assertEqual(request.get_header("Authorization"), "Bearer test-token")
        self.assertEqual(
            json.loads(request.data),
            {
                "senderID": "SALAMA",
                "phone": "+254700000000",
                "message": "Emergency alert",
            },
        )

    @patch("emergency_notifications.providers.MobileSasaProvider.send_sms")
    def test_management_command_processes_only_selected_notification(
        self,
        send_sms,
    ):
        from .providers import SMSResult

        send_sms.return_value = SMSResult(
            accepted=True,
            provider_message_id="MS-SELECTED",
            provider_status="0200",
        )
        selected = self.create_notification()
        other_contact = TrustedContact.objects.create(
            user=self.user,
            name="Second Trusted Contact",
            phone_number="+254711111111",
            relationship="Test contact",
            is_active=True,
            receive_sos_alerts=True,
            consent_confirmed=True,
            consent_confirmed_at=timezone.now(),
        )
        other = EmergencyNotification.objects.create(
            incident=self.incident,
            recipient=other_contact,
            channel="sms",
            status=EmergencyNotification.Status.PENDING,
        )

        call_command(
            "process",
            "--notification-id",
            str(selected.pk),
            stdout=StringIO(),
        )

        selected.refresh_from_db()
        other.refresh_from_db()
        self.assertEqual(selected.status, EmergencyNotification.Status.ACCEPTED)
        self.assertEqual(other.status, EmergencyNotification.Status.PENDING)
        send_sms.assert_called_once()

    def test_non_sos_notification_is_not_sent(self):
        notification = self.create_notification()

        self.incident.source = Incident.IncidentSource.MOBILE
        self.incident.is_sos = False
        self.incident.save(update_fields=["source", "is_sos"])

        fake_provider = Mock()

        result = process_emergency_notification(
            notification.pk,
            provider=fake_provider,
        )

        self.assertEqual(
            result.status,
            EmergencyNotification.Status.FAILED,
        )

        fake_provider.send_sms.assert_not_called()


class VoiceNotificationTests(EmergencyNotificationTestBase):
    def test_voice_queue_requires_its_own_opt_in(self):
        self.assertEqual(queue_voice_notifications(self.incident), [])

        self.contact.receive_sos_alerts = False
        self.contact.consent_confirmed = False
        self.contact.receive_voice_calls = True
        self.contact.save(update_fields=[
            "receive_sos_alerts",
            "consent_confirmed",
            "receive_voice_calls",
        ])

        queued = queue_voice_notifications(self.incident)

        self.assertEqual(len(queued), 1)
        self.assertEqual(queued[0].channel, "voice")

    def test_queueing_same_incident_twice_does_not_duplicate_calls(self):
        self.contact.receive_voice_calls = True
        self.contact.save(update_fields=["receive_voice_calls"])

        first = queue_voice_notifications(self.incident)
        second = queue_voice_notifications(self.incident)

        self.assertEqual(len(first), 1)
        self.assertEqual(second, [])
        self.assertEqual(
            EmergencyNotification.objects.filter(
                incident=self.incident,
                recipient=self.contact,
                channel="voice",
            ).count(),
            1,
        )

    def test_announcement_avoids_name_and_precise_coordinates(self):
        self.incident.latitude = -1.286389
        self.incident.longitude = 36.817223
        self.incident.save(update_fields=["latitude", "longitude"])
        self.user.first_name = "Amina"
        self.user.last_name = "Wanjiku"
        self.user.save(update_fields=["first_name", "last_name"])

        announcement = generate_emergency_voice_announcement(
            self.incident
        )

        self.assertIn("trusted contact needs help", announcement)
        self.assertNotIn("Amina Wanjiku", announcement)
        self.assertNotIn("-1.286389", announcement)
        self.assertNotIn("36.817223", announcement)

    def test_mock_provider_accepts_call_and_records_provider_call_id(self):
        self.contact.receive_voice_calls = True
        self.contact.save(update_fields=["receive_voice_calls"])
        notification = queue_voice_notifications(self.incident)[0]

        result = process_voice_notification(
            notification.pk,
            provider=MockVoiceProvider(),
        )

        self.assertEqual(result.status, EmergencyNotification.Status.ACCEPTED)
        self.assertTrue(result.provider_message_id.startswith("MOCK-"))
        self.assertEqual(result.provider_status, "simulated")
        self.assertEqual(result.attempt_count, 1)

    def test_call_is_not_processed_after_voice_consent_is_revoked(self):
        self.contact.receive_voice_calls = True
        self.contact.save(update_fields=["receive_voice_calls"])
        notification = queue_voice_notifications(self.incident)[0]
        self.contact.receive_voice_calls = False
        self.contact.save(update_fields=["receive_voice_calls"])
        provider = Mock()

        result = process_voice_notification(
            notification.pk,
            provider=provider,
        )

        self.assertEqual(result.status, EmergencyNotification.Status.FAILED)
        provider.initiate_call.assert_not_called()

    def test_provider_exception_marks_call_outcome_unknown(self):
        self.contact.receive_voice_calls = True
        self.contact.save(update_fields=["receive_voice_calls"])
        notification = queue_voice_notifications(self.incident)[0]
        provider = Mock()
        provider.initiate_call.side_effect = TimeoutError("timeout")

        result = process_voice_notification(
            notification.pk,
            provider=provider,
        )

        self.assertEqual(result.status, EmergencyNotification.Status.UNKNOWN)
        self.assertEqual(result.provider_status, "unknown")
        self.assertEqual(result.attempt_count, 1)

    def test_voice_processing_does_not_send_sms_notifications(self):
        notification = self.create_notification()
        provider = Mock()

        result = process_voice_notification(notification.pk, provider=provider)

        self.assertEqual(result.status, EmergencyNotification.Status.FAILED)
        provider.initiate_call.assert_not_called()

    def test_rejected_call_records_provider_status_and_error(self):
        self.contact.receive_voice_calls = True
        self.contact.save(update_fields=["receive_voice_calls"])
        notification = queue_voice_notifications(self.incident)[0]
        provider = Mock()
        provider.initiate_call.return_value = VoiceCallResult(
            accepted=False,
            provider_status="rejected",
            error="Invalid destination",
        )

        result = process_voice_notification(
            notification.pk,
            provider=provider,
        )

        self.assertEqual(result.status, EmergencyNotification.Status.FAILED)
        self.assertEqual(result.provider_status, "rejected")
        self.assertEqual(result.last_error, "Invalid destination")
        self.assertEqual(result.attempt_count, 1)

    @override_settings(
        AT_VOICE_USERNAME="salama-test",
        AT_VOICE_API_KEY="test-api-key",
        AT_VOICE_NUMBER="+254700000000",
        AT_VOICE_BASE_URL="https://voice.africastalking.com",
        AT_VOICE_CALLBACK_URL=(
            "https://api.example.test/api/emergency-notifications/"
            "voice/callback/?token=callback-secret"
        ),
        AT_VOICE_CALLBACK_TOKEN="callback-secret",
    )
    @patch("emergency_notifications.voice_provider.urlopen")
    def test_africas_talking_provider_authenticates_and_parses_call(
        self,
        urlopen,
    ):
        response = Mock()
        response.read.return_value = (
            b'{"entries":[{"status":"Queued","sessionId":"AT-SESSION-1"}],'
            b'"errorMessage":""}'
        )
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        urlopen.return_value = response

        result = AfricasTalkingVoiceProvider().initiate_call(
            "+254711111111",
            "Emergency announcement",
            "notification-1",
        )

        self.assertTrue(result.accepted)
        self.assertEqual(result.provider_call_id, "AT-SESSION-1")
        self.assertEqual(result.provider_status, "Queued")
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "https://voice.africastalking.com/call")
        self.assertEqual(request.get_method(), "POST")
        headers = {
            key.lower(): value for key, value in request.header_items()
        }
        self.assertEqual(headers["apikey"], "test-api-key")
        payload = parse_qs(request.data.decode("utf-8"))
        self.assertEqual(payload["username"], ["salama-test"])
        self.assertEqual(payload["from"], ["+254700000000"])
        self.assertEqual(payload["to"], ["+254711111111"])

    @override_settings(AT_VOICE_CALLBACK_TOKEN="callback-secret")
    def test_voice_callback_tracks_progress_and_returns_private_announcement(
        self,
    ):
        notification = EmergencyNotification.objects.create(
            incident=self.incident,
            recipient=self.contact,
            channel="voice",
            status=EmergencyNotification.Status.ACCEPTED,
            provider_message_id="AT-SESSION-2",
        )
        client = APIClient()
        endpoint = (
            reverse("africas-talking-voice-callback")
            + "?token=callback-secret"
        )

        ringing = client.post(
            endpoint,
            {"sessionId": "AT-SESSION-2", "status": "Ringing"},
        )
        self.assertEqual(ringing.status_code, 200)
        notification.refresh_from_db()
        self.assertEqual(notification.status, EmergencyNotification.Status.RINGING)

        answered = client.post(
            endpoint,
            {"sessionId": "AT-SESSION-2", "isActive": "1"},
        )
        self.assertEqual(answered.status_code, 200)
        self.assertIn(b"<Say>", answered.content)
        notification.refresh_from_db()
        self.assertEqual(notification.status, EmergencyNotification.Status.ANSWERED)

        completed = client.post(
            endpoint,
            {"sessionId": "AT-SESSION-2", "status": "Completed"},
        )
        self.assertEqual(completed.status_code, 200)
        notification.refresh_from_db()
        self.assertEqual(
            notification.status,
            EmergencyNotification.Status.COMPLETED,
        )

        replayed = client.post(
            endpoint,
            {"sessionId": "AT-SESSION-2", "status": "Ringing"},
        )
        self.assertEqual(replayed.status_code, 200)
        notification.refresh_from_db()
        self.assertEqual(
            notification.status,
            EmergencyNotification.Status.COMPLETED,
        )

    @override_settings(AT_VOICE_CALLBACK_TOKEN="callback-secret")
    def test_voice_callback_rejects_bad_token_and_unknown_session(self):
        client = APIClient()
        endpoint = reverse("africas-talking-voice-callback")

        unauthorized = client.post(
            endpoint + "?token=wrong",
            {"sessionId": "AT-SESSION-3", "status": "Answered"},
        )
        self.assertEqual(unauthorized.status_code, 403)

        missing = client.post(
            endpoint + "?token=callback-secret",
            {"sessionId": "AT-UNKNOWN", "status": "Answered"},
        )
        self.assertEqual(missing.status_code, 404)

    @override_settings(
        EMERGENCY_NOTIFICATION_PROCESSING_TIMEOUT_MINUTES=1,
    )
    @patch("emergency_notifications.tasks.process_notification.delay")
    def test_recovery_marks_stale_processing_unknown_without_redial(
        self,
        enqueue,
    ):
        from .tasks import recover_notifications

        stale = self.create_notification()
        stale.status = EmergencyNotification.Status.PROCESSING
        stale.save(update_fields=["status"])
        EmergencyNotification.objects.filter(pk=stale.pk).update(
            updated_at=timezone.now() - timedelta(minutes=2)
        )
        pending_contact = TrustedContact.objects.create(
            user=self.user,
            name="Pending voice contact",
            phone_number="+254711111111",
            receive_voice_calls=True,
        )
        pending = EmergencyNotification.objects.create(
            incident=self.incident,
            recipient=pending_contact,
            channel="voice",
            status=EmergencyNotification.Status.PENDING,
        )

        self.assertEqual(recover_notifications.run(), 1)

        stale.refresh_from_db()
        self.assertEqual(stale.status, EmergencyNotification.Status.UNKNOWN)
        self.assertIn("redial was suppressed", stale.last_error)
        enqueue.assert_called_once_with(str(pending.pk))

    @override_settings(AT_VOICE_MODE="mock")
    @patch("emergency_notifications.voice_provider.MockVoiceProvider.initiate_call")
    @patch("emergency_notifications.providers.ConsoleSMSProvider.send_sms")
    def test_management_command_processes_selected_voice_notification(
        self,
        send_sms,
        initiate_call,
    ):
        self.contact.receive_voice_calls = True
        self.contact.save(update_fields=["receive_voice_calls"])
        notification = queue_voice_notifications(self.incident)[0]
        initiate_call.return_value = VoiceCallResult(
            accepted=True,
            provider_call_id="VOICE-SELECTED",
            provider_status="simulated",
        )

        call_command(
            "process",
            "--notification-id",
            str(notification.pk),
            stdout=StringIO(),
        )

        notification.refresh_from_db()
        self.assertEqual(
            notification.status,
            EmergencyNotification.Status.ACCEPTED,
        )
        self.assertEqual(
            notification.provider_message_id,
            "VOICE-SELECTED",
        )
        initiate_call.assert_called_once()
        send_sms.assert_not_called()