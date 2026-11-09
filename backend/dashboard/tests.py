from django.test import TestCase
from dashboard.models import (
    IncidentAuditEvent,
    IncidentReviewNote,
)

from datetime import timedelta
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from incidents.models import Incident
from notifications.models import Notification


User = get_user_model()


class DashboardOverviewApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.survivor = User.objects.create_user(
            username="overview_survivor",
            email="overview_survivor@example.test",
            password="test-password",
            role=User.Role.SURVIVOR,
        )
        self.other_survivor = User.objects.create_user(
            username="overview_other_survivor",
            email="overview_other_survivor@example.test",
            password="test-password",
            role=User.Role.SURVIVOR,
        )
        self.incident = Incident.objects.create(
            user=self.survivor,
            source=Incident.IncidentSource.MOBILE,
            threat_level=Incident.ThreatLevel.HIGH,
            description="Mobile-created incident",
            occurred_at=timezone.now(),
            latitude=-1.286389,
            longitude=36.817223,
            client_event_id=__import__("uuid").uuid4(),
        )
        Incident.objects.create(
            user=self.other_survivor,
            source=Incident.IncidentSource.MOBILE,
            description="Another survivor's incident",
            occurred_at=timezone.now(),
            client_event_id=__import__("uuid").uuid4(),
        )
        self.endpoint = reverse("dashboard-overview")

    def test_authenticated_survivor_gets_owned_incidents_as_json(self):
        self.client.force_authenticate(user=self.survivor)

        response = self.client.get(self.endpoint)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")
        incidents = response.data["incidents"]
        self.assertEqual(len(incidents), 1)
        self.assertEqual(incidents[0]["id"], str(self.incident.id))
        self.assertEqual(
            incidents[0]["client_event_id"],
            str(self.incident.client_event_id),
        )
        self.assertEqual(incidents[0]["description"], "Mobile-created incident")
        self.assertEqual(str(incidents[0]["latitude"]), "-1.286389")
        self.assertEqual(str(incidents[0]["longitude"]), "36.817223")

    def test_admin_role_without_staff_access_sees_only_own_incidents(self):
        non_staff_admin = User.objects.create_user(
            username="overview_non_staff_admin",
            email="overview_non_staff_admin@example.test",
            password="test-password",
            role=User.Role.ADMIN,
        )
        own_incident = Incident.objects.create(
            user=non_staff_admin,
            source=Incident.IncidentSource.MOBILE,
            occurred_at=timezone.now(),
            client_event_id=__import__("uuid").uuid4(),
        )
        self.client.force_authenticate(user=non_staff_admin)

        response = self.client.get(self.endpoint)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [incident["id"] for incident in response.data["incidents"]],
            [str(own_incident.id)],
        )

    def test_anonymous_user_cannot_get_dashboard_overview(self):
        response = self.client.get(self.endpoint)

        self.assertIn(response.status_code, [401, 403])


class IncidentDashboardTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.survivor = User.objects.create_user(
            username="survivor_one",
            email="survivor_one@example.test",
            password="TestPassword-123!",
            role="survivor",
        )

        cls.other_survivor = User.objects.create_user(
            username="survivor_two",
            email="survivor_two@example.test",
            password="TestPassword-456!",
            role="survivor",
        )

        cls.admin = User.objects.create_user(
            username="dashboard_admin",
            email="dashboard_admin@example.test",
            password="TestPassword-789!",
            role="admin",
            is_staff=True,
        )

        cls.incident = Incident.objects.create(
            user=cls.survivor,
            source="mobile",
            threat_level="high",
            description="Dashboard test incident",
            occurred_at=timezone.now() - timedelta(minutes=10),
            client_event_id=(
                __import__("uuid").uuid4()
            ),
        )

    def test_dashboard_requires_login(self):
        response = self.client.get(
            reverse("dashboard:incident_list")
        )

        self.assertNotEqual(response.status_code, 200)

    def test_survivor_can_view_dashboard(self):
        self.client.force_login(self.survivor)

        response = self.client.get(
            reverse("dashboard:incident_list")
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            str(self.incident.id),
        )

    def test_survivor_cannot_view_another_survivors_incident(self):
        self.client.force_login(self.other_survivor)

        response = self.client.get(
            reverse(
                "dashboard:incident_detail",
                kwargs={"incident_id": self.incident.id},
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_dashboard_summary_counts_owned_incidents(self):
        self.client.force_login(self.survivor)

        response = self.client.get(
            reverse("dashboard:incident_list")
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["summary"]["total"], 1)
        self.assertEqual(
            response.context["summary"]["high_priority"],
            1,
        )

    def test_support_worker_without_assignment_cannot_view_incident(self):
        support_worker = User.objects.create_user(
            username="support_worker_one",
            email="support_worker_one@example.test",
            password="SupportPassword-123!",
            role="support_worker",
        )

        self.client.force_login(support_worker)

        response = self.client.get(
            reverse(
                "dashboard:incident_detail",
                kwargs={"incident_id": self.incident.id},
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_trusted_contact_role_does_not_grant_incident_access(self):
        trusted_contact = User.objects.create_user(
            username="trusted_contact_one",
            email="trusted_contact_one@example.test",
            password="ContactPassword-123!",
            role="trusted_contact",
        )

        self.client.force_login(trusted_contact)

        response = self.client.get(
            reverse("dashboard:incident_list")
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["summary"]["total"],
            0,
        )
        


class IncidentReviewAndAuditModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.survivor = User.objects.create_user(
            username="review_test_survivor",
            email="review_survivor@example.test",
            password="TestPassword-123!",
            role="survivor",
        )

        cls.incident = Incident.objects.create(
            user=cls.survivor,
            source="mobile",
            threat_level="medium",
            description="Review and audit test",
            occurred_at=timezone.now(),
            client_event_id=__import__("uuid").uuid4(),
        )
    def test_incident_view_audit_event_is_recorded(self):
        self.client.force_login(self.survivor)

        response = self.client.get(
            reverse(
                "dashboard:incident_detail",
                kwargs={"incident_id": self.incident.id},
            )
        )

        self.assertEqual(response.status_code, 200)

        self.assertTrue(
            IncidentAuditEvent.objects.filter(
                actor=self.survivor,
                incident=self.incident,
                action=IncidentAuditEvent.Action.INCIDENT_VIEWED,
                outcome=IncidentAuditEvent.Outcome.SUCCESS,
            ).exists()
        )
    def test_review_note_can_be_created(self):
        note = IncidentReviewNote.objects.create(
            incident=self.incident,
            author=self.survivor,
            note="Test review note.",
        )

        self.assertEqual(
            note.incident_id,
            self.incident.id,
        )

        self.assertEqual(
            note.note,
            "Test review note.",
        )

    def test_admin_review_note_notifies_administrators(self):
        admin = User.objects.create_user(
            username="review_note_admin",
            email="review_note_admin@example.test",
            password="test-password",
            role=User.Role.ADMIN,
            is_staff=True,
        )
        self.client.force_login(admin)

        response = self.client.post(
            reverse(
                "dashboard:create_review_note",
                kwargs={"incident_id": self.incident.id},
            ),
            {"note": "The report has been reviewed."},
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Notification.objects.filter(
                recipient=admin,
                incident=self.incident,
                title="Incident review note added",
            ).exists()
        )

    def test_audit_event_can_be_created(self):
        event = IncidentAuditEvent.objects.create(
            actor=self.survivor,
            incident=self.incident,
            action=IncidentAuditEvent.Action.INCIDENT_VIEWED,
            outcome=IncidentAuditEvent.Outcome.SUCCESS,
        )

        self.assertEqual(
            event.actor_id,
            self.survivor.id,
        )

        self.assertEqual(
            event.incident_id,
            self.incident.id,
        )

    def test_audit_event_can_record_access_denied(self):
        event = IncidentAuditEvent.objects.create(
            actor=self.survivor,
            incident=self.incident,
            action=IncidentAuditEvent.Action.ACCESS_DENIED,
            outcome=IncidentAuditEvent.Outcome.FAILURE,
        )

        self.assertEqual(
            event.action,
            "access_denied",
        )

        self.assertEqual(
            event.outcome,
            "failure",
        )