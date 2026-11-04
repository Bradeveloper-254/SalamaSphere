from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from rest_framework.test import APIClient

from accounts.models import User
from notifications.models import Notification

from .models import Incident, IncidentAssignment


class IncidentAssignmentWorkflowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            username="workflow_admin",
            email="workflow_admin@example.com",
            password="test-password",
            role=User.Role.ADMIN,
            is_staff=True,
        )
        self.owner = User.objects.create_user(
            username="incident_owner",
            email="incident_owner@example.com",
            password="test-password",
        )
        self.incident = Incident.objects.create(
            user=self.owner,
            source=Incident.IncidentSource.MOBILE,
            threat_level=Incident.ThreatLevel.HIGH,
            description="Test incident",
            occurred_at=timezone.now(),
            latitude=-1.2864,
            longitude=36.8172,
        )

    def _authority(self, username, latitude, longitude, available=True):
        return User.objects.create_user(
            username=username,
            email=f"{username}@example.com",
            password="test-password",
            role=User.Role.AUTHORITY,
            authority_status=User.AuthorityStatus.APPROVED,
            is_available=available,
            last_known_latitude=latitude,
            last_known_longitude=longitude,
            location_updated_at=timezone.now(),
        )

    def test_candidates_are_nearest_available_and_not_busy(self):
        nearest = self._authority("nearest", -1.287, 36.817)
        farther = self._authority("farther", -1.30, 36.82)
        busy = self._authority("busy", -1.286, 36.817)
        other_incident = Incident.objects.create(
            user=self.owner,
            source=Incident.IncidentSource.MOBILE,
            occurred_at=timezone.now(),
        )
        IncidentAssignment.objects.create(
            incident=other_incident,
            authority=busy,
            assigned_by=self.admin,
        )
        self.client.force_authenticate(self.admin)

        response = self.client.get(
            reverse("admin-assignable-authorities"),
            {"incident_id": self.incident.id},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["id"] for item in response.data],
            [nearest.id, farther.id],
        )

    def test_new_incident_notifies_owner_and_active_administrators(self):
        self.client.force_authenticate(self.owner)

        response = self.client.post(
            reverse("incident-list-create"),
            {
                "source": Incident.IncidentSource.MOBILE,
                "threat_level": Incident.ThreatLevel.MEDIUM,
                "description": "New report",
                "occurred_at": timezone.now().isoformat(),
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.data)
        incident_id = response.data["id"]
        self.assertEqual(
            set(
                Notification.objects.filter(incident_id=incident_id)
                .values_list("recipient_id", flat=True)
            ),
            {self.owner.id, self.admin.id},
        )

    def test_assignment_marks_authority_busy_and_notifies_recipients(self):
        authority = self._authority("assigned_authority", -1.287, 36.817)
        self.client.force_authenticate(self.admin)

        response = self.client.post(
            reverse("admin-incident-assignment-create"),
            {
                "incident_id": str(self.incident.id),
                "authority_id": authority.id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200, response.data)
        authority.refresh_from_db()
        self.assertFalse(authority.is_available)
        self.assertTrue(
            IncidentAssignment.objects.filter(
                incident=self.incident,
                authority=authority,
                is_active=True,
            ).exists()
        )
        self.assertEqual(
            Notification.objects.filter(
                recipient__in=[self.owner, authority],
                incident=self.incident,
            ).count(),
            2,
        )

    def test_assignment_rejects_authority_with_an_active_case(self):
        authority = self._authority("busy_authority", -1.287, 36.817)
        other_incident = Incident.objects.create(
            user=self.owner,
            source=Incident.IncidentSource.MOBILE,
            occurred_at=timezone.now(),
        )
        IncidentAssignment.objects.create(
            incident=other_incident,
            authority=authority,
            assigned_by=self.admin,
        )
        self.client.force_authenticate(self.admin)

        response = self.client.post(
            reverse("admin-incident-assignment-create"),
            {
                "incident_id": str(self.incident.id),
                "authority_id": authority.id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(
            IncidentAssignment.objects.filter(
                incident=self.incident,
                is_active=True,
            ).exists()
        )

    def test_authority_can_resolve_assigned_case_and_notifications_are_created(self):
        authority = self._authority("resolving_authority", -1.287, 36.817)
        assignment = IncidentAssignment.objects.create(
            incident=self.incident,
            authority=authority,
            assigned_by=self.admin,
        )
        self.client.force_authenticate(authority)

        response = self.client.post(
            reverse(
                "authority-resolve-incident",
                kwargs={"incident_id": self.incident.id},
            ),
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 200, response.data)
        self.incident.refresh_from_db()
        assignment.refresh_from_db()
        self.assertEqual(self.incident.status, Incident.IncidentStatus.CLOSED)
        self.assertFalse(assignment.is_active)
        self.assertEqual(
            Notification.objects.filter(incident=self.incident).count(),
            3,
        )


class NotificationReadStateTests(TestCase):
    def test_recipient_can_mark_notification_read(self):
        user = User.objects.create_user(
            username="notification_user",
            email="notification_user@example.com",
            password="test-password",
        )
        notification = Notification.objects.create(
            recipient=user,
            title="Incident update",
            message="A case was assigned.",
        )
        client = APIClient()
        client.force_authenticate(user)

        response = client.patch(
            reverse("notification-detail", kwargs={"pk": notification.id}),
            {"is_read": True},
            format="json",
        )

        self.assertEqual(response.status_code, 200, response.data)
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)
