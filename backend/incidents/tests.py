import uuid
from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from rest_framework.test import APIClient

from accounts.models import User
from devices.models import WearableDevice
from emergency_notifications.models import EmergencyNotification
from trusted_contacts.models import TrustedContact
from .models import Incident


class IncidentAPITest(TestCase):

    def setUp(self):
        self.client = APIClient()

        self.user = User.objects.create_user(
            username="incident_api_user",
            email="incident_api@example.com",
            password="TestPassword123!",
        )

        self.device = WearableDevice.objects.create(
            owner=self.user,
            device_name="Test SalamaSphere Wearable",
            device_identifier="SALAMA-TEST-001",
            firmware_version="1.0.0",
            status=WearableDevice.DeviceStatus.ACTIVE,
        )

        self.client.force_authenticate(user=self.user)

        self.endpoint = reverse("incident-list-create")

    def test_anonymous_user_cannot_list_incidents(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(self.endpoint)

        self.assertIn(response.status_code, [401, 403])

    def test_first_submission_creates_incident(self):
        event_id = str(uuid.uuid4())

        response = self.client.post(
            self.endpoint,
            self.build_payload(event_id),
            format="json",
        )

        self.assertEqual(response.status_code, 201)

        self.assertEqual(
            Incident.objects.filter(
                user=self.user,
                client_event_id=event_id,
            ).count(),
            1,
        )

    def test_repeated_submission_does_not_create_duplicate(self):
        event_id = str(uuid.uuid4())
        payload = self.build_payload(event_id)

        first_response = self.client.post(
            self.endpoint,
            payload,
            format="json",
        )

        self.assertEqual(
            first_response.status_code,
            201,
            msg=str(first_response.data),
        )

        second_response = self.client.post(
            self.endpoint,
            payload,
            format="json",
        )

        self.assertEqual(
            second_response.status_code,
            200,
            msg=str(second_response.data),
        )

        self.assertEqual(
            str(first_response.data["id"]),
            str(second_response.data["id"]),
        )

        self.assertEqual(
            Incident.objects.filter(
                user=self.user,
                client_event_id=event_id,
            ).count(),
            1,
        )

    def test_inactive_device_cannot_submit_incident(self):
        self.device.status = WearableDevice.DeviceStatus.INACTIVE
        self.device.save()

        response = self.client.post(
            self.endpoint,
            self.build_payload(str(uuid.uuid4())),
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_wearable_sos_queues_notifications_for_consented_contact(self):
        TrustedContact.objects.create(
            user=self.user,
            name="Trusted contact",
            phone_number="+254700000000",
            is_active=True,
            receive_sos_alerts=True,
            consent_confirmed=True,
        )

        response = self.client.post(
            self.endpoint,
            {
                **self.build_payload(str(uuid.uuid4())),
                "is_sos": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201, msg=str(response.data))
        self.assertTrue(response.data["is_sos"])
        self.assertEqual(
            EmergencyNotification.objects.filter(
                incident_id=response.data["id"],
                status=EmergencyNotification.Status.PENDING,
            ).count(),
            1,
        )

    def test_mobile_sos_is_rejected(self):
        payload = self.build_payload(str(uuid.uuid4()))
        payload.update(source="mobile", is_sos=True)

        response = self.client.post(
            self.endpoint,
            payload,
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(EmergencyNotification.objects.count(), 0)

    def test_sos_status_cannot_be_changed_after_creation(self):
        response = self.client.post(
            self.endpoint,
            self.build_payload(str(uuid.uuid4())),
            format="json",
        )
        self.assertEqual(response.status_code, 201)

        update_response = self.client.patch(
            f"{self.endpoint}{response.data['id']}/",
            {"is_sos": True},
            format="json",
        )

        self.assertEqual(update_response.status_code, 400)

    def build_payload(self, event_id):
        return {
            "client_event_id": event_id,
            "device_identifier": self.device.device_identifier,
            "source": "wearable",
            "threat_level": "medium",
            "description": "Synthetic incident for automated testing.",
            "occurred_at": timezone.now().isoformat(),
        }


class IncidentModelTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="incident_model_user",
            email="incident_model@example.com",
            password="TestPassword123!",
        )

    def test_incident_can_be_created(self):
        incident = Incident.objects.create(
            user=self.user,
            source=Incident.IncidentSource.MOBILE,
            threat_level=Incident.ThreatLevel.HIGH,
            occurred_at=timezone.now() - timedelta(minutes=5),
            description="Synthetic test incident.",
        )

        self.assertEqual(
            incident.threat_level,
            Incident.ThreatLevel.HIGH,
        )

        self.assertEqual(incident.user, self.user)