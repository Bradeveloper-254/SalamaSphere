from datetime import timedelta
from unittest.mock import Mock

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from devices.models import WearableDevice
from incidents.models import Incident
from trusted_contacts.models import TrustedContact

from .models import EmergencyNotification
from .services import (
    queue_emergency_notifications,
    process_emergency_notification,
)
from .providers import ConsoleSMSProvider


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
        return EmergencyNotification.objects.create(
            incident=incident or self.incident,
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

    def test_ordinary_wearable_incident_does_not_queue(self):
        self.incident.is_sos = False
        self.incident.save(update_fields=["is_sos"])

        queued = queue_emergency_notifications(self.incident)

        self.assertEqual(queued, [])
        self.assertEqual(
            EmergencyNotification.objects.count(),
            0,
        )

    def test_mobile_sos_does_not_queue_wearable_notifications(self):
        self.incident.source = Incident.IncidentSource.MOBILE
        self.incident.save(update_fields=["source"])

        queued = queue_emergency_notifications(self.incident)

        self.assertEqual(queued, [])
        self.assertEqual(
            EmergencyNotification.objects.count(),
            0,
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
    def test_simulated_provider_accepts_notification(self):
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

    def test_non_sos_notification_is_not_sent(self):
        notification = self.create_notification()

        self.incident.is_sos = False
        self.incident.save(update_fields=["is_sos"])

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