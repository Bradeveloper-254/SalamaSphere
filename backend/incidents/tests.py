import uuid
from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from rest_framework.test import APIClient

from accounts.models import User
from devices.models import WearableDevice
from dashboard.models import IncidentAuditEvent
from emergency_notifications.models import EmergencyNotification
from notifications.models import Notification
from threat_analysis.models import ThreatAssessment
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

    def test_admin_can_list_and_retrieve_survivor_incidents(self):
        survivor = User.objects.create_user(
            username="admin_visible_survivor",
            email="admin_visible_survivor@example.com",
            password="test-password",
            role=User.Role.SURVIVOR,
        )
        incident = Incident.objects.create(
            user=survivor,
            source=Incident.IncidentSource.MOBILE,
            description="Survivor report for admin review",
            occurred_at=timezone.now(),
        )
        admin = User.objects.create_user(
            username="incident_view_admin",
            email="incident_view_admin@example.com",
            password="test-password",
            role=User.Role.ADMIN,
            is_staff=True,
        )
        self.client.force_authenticate(user=admin)

        list_response = self.client.get(self.endpoint)
        detail_response = self.client.get(
            reverse("incident-detail", kwargs={"id": incident.id}),
        )

        self.assertEqual(list_response.status_code, 200)
        self.assertIn(
            str(incident.id),
            {item["id"] for item in list_response.data},
        )
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(detail_response.data["id"], str(incident.id))

        update_response = self.client.patch(
            reverse("incident-detail", kwargs={"id": incident.id}),
            {"description": "Changed by administrator"},
            format="json",
        )
        self.assertEqual(update_response.status_code, 403)
        incident.refresh_from_db()
        self.assertEqual(
            incident.description,
            "Survivor report for admin review",
        )

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
        incident = Incident.objects.get(client_event_id=event_id)
        self.device.refresh_from_db()
        self.assertIsNotNone(self.device.last_seen_at)
        assessment = ThreatAssessment.objects.get(incident=incident)
        self.assertEqual(assessment.final_level, incident.threat_level)
        self.assertTrue(
            IncidentAuditEvent.objects.filter(
                incident=incident,
                action=IncidentAuditEvent.Action.INCIDENT_CREATED,
                outcome=IncidentAuditEvent.Outcome.SUCCESS,
            ).exists()
        )
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.user,
                incident=incident,
            ).exists()
        )

    def test_keywords_escalate_a_reported_threat_and_are_saved(self):
        response = self.client.post(
            self.endpoint,
            {
                **self.build_payload(str(uuid.uuid4())),
                "threat_level": "low",
                "description": "The person threatened to kill me.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.data)
        incident = Incident.objects.get(pk=response.data["id"])
        assessment = ThreatAssessment.objects.get(incident=incident)
        self.assertEqual(incident.threat_level, Incident.ThreatLevel.HIGH)
        self.assertEqual(assessment.suggested_level, "high")
        self.assertTrue(assessment.needs_review)
        self.assertIn(
            "kill me",
            assessment.indicators["keyword_matches"]["high"],
        )
        self.assertIn(
            "threatened",
            assessment.indicators["keyword_matches"]["medium"],
        )

    def test_incident_rejects_invalid_coordinates_and_accuracy(self):
        payload = self.build_payload(str(uuid.uuid4()))
        payload.update(latitude=91, longitude=36, location_accuracy_m=-1)

        response = self.client.post(
            self.endpoint,
            payload,
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(Incident.objects.exists())

    def test_mobile_report_can_be_created_without_a_wearable(self):
        response = self.client.post(
            self.endpoint,
            {
                "source": Incident.IncidentSource.MOBILE,
                "threat_level": Incident.ThreatLevel.MEDIUM,
                "description": "Mobile evidence report",
                "occurred_at": timezone.now().isoformat(),
                "latitude": -1.2864,
                "longitude": 36.8172,
                "location_accuracy_m": 8.5,
                "location_source": "mobile_gps",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.data)
        incident = Incident.objects.get(id=response.data["id"])
        self.assertIsNone(incident.device_id)
        self.assertEqual(incident.user_id, self.user.id)
        self.assertEqual(float(incident.latitude), -1.2864)
        self.assertEqual(float(incident.longitude), 36.8172)
        self.assertEqual(incident.location_accuracy_m, 8.5)
        self.assertEqual(incident.location_source, "mobile_gps")

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

    def test_user_cannot_submit_with_another_users_device(self):
        other_user = User.objects.create_user(
            username="foreign_device_owner",
            email="foreign_device@example.com",
            password="test-password",
        )
        foreign_device = WearableDevice.objects.create(
            owner=other_user,
            device_name="Another user's wearable",
            device_identifier="SALAMA-FOREIGN-001",
            status=WearableDevice.DeviceStatus.ACTIVE,
        )
        payload = self.build_payload(str(uuid.uuid4()))
        payload["device_identifier"] = foreign_device.device_identifier

        response = self.client.post(
            self.endpoint,
            payload,
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(Incident.objects.exists())

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

    def test_mobile_sos_without_wearable_queues_alerts(self):
        TrustedContact.objects.create(
            user=self.user,
            name="Trusted contact",
            phone_number="+254700000000",
            is_active=True,
            receive_sos_alerts=True,
            consent_confirmed=True,
        )
        payload = self.build_payload(str(uuid.uuid4()))
        payload.update(source="mobile", is_sos=True)
        payload.pop("device_identifier")

        response = self.client.post(
            self.endpoint,
            payload,
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