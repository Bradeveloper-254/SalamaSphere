from datetime import timedelta
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from incidents.models import Incident, IncidentAssignment

from .models import Notification
from .services import notify_case_assigned, notify_case_resolved, notify_new_incident

User = get_user_model()


class NotificationWorkflowTests(TestCase):
    def setUp(self):
        self.survivor = User.objects.create_user(
            username="survivor",
            email="survivor@example.test",
            password="test-password",
            role=User.Role.SURVIVOR,
        )
        self.authority = User.objects.create_user(
            username="authority",
            email="authority@example.test",
            password="test-password",
            role=User.Role.AUTHORITY,
            authority_status=User.AuthorityStatus.APPROVED,
        )
        self.admin = User.objects.create_user(
            username="admin",
            email="admin@example.test",
            password="test-password",
            role=User.Role.ADMIN,
            is_staff=True,
        )
        self.incident = Incident.objects.create(
            user=self.survivor,
            source=Incident.IncidentSource.MOBILE,
            threat_level=Incident.ThreatLevel.HIGH,
            occurred_at=timezone.now(),
        )
        self.assignment = IncidentAssignment.objects.create(
            incident=self.incident,
            authority=self.authority,
            assigned_by=self.admin,
        )

    def test_new_incident_notifies_survivor_admin_and_approved_authorities(self):
        notify_new_incident(self.incident)

        self.assertTrue(
            Notification.objects.filter(
                recipient=self.survivor,
                title="Incident received",
            ).exists()
        )
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.admin,
                title="New incident uploaded",
            ).exists()
        )
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.authority,
                title="New incident submitted",
            ).exists()
        )

    def test_assignment_and_resolution_notify_involved_users_and_admin(self):
        notify_case_assigned(self.assignment)
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.admin,
                title="Case assignment completed",
            ).exists()
        )

        notify_case_resolved(self.assignment)
        for recipient in (self.survivor, self.authority, self.admin):
            self.assertTrue(
                Notification.objects.filter(
                    recipient=recipient,
                    title="Incident resolved",
                ).exists()
            )

    def test_authority_can_message_admin_and_assigned_survivor(self):
        client = APIClient()
        client.force_authenticate(user=self.authority)

        recipients = client.get("/api/notifications/messages/recipients/")
        self.assertEqual(recipients.status_code, 200)
        self.assertEqual(
            {item["id"] for item in recipients.data},
            {self.admin.pk, self.survivor.pk},
        )

        response = client.post(
            "/api/notifications/messages/",
            {"recipient_id": self.survivor.pk, "message": "I have an update."},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.survivor,
                title="Message from authority",
                message="I have an update.",
            ).exists()
        )

    def test_authority_cannot_message_an_unassigned_survivor(self):
        other_survivor = User.objects.create_user(
            username="other-survivor",
            email="other-survivor@example.test",
            password="test-password",
            role=User.Role.SURVIVOR,
        )
        client = APIClient()
        client.force_authenticate(user=self.authority)

        response = client.post(
            "/api/notifications/messages/",
            {"recipient_id": other_survivor.pk, "message": "Hello."},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_overdue_reminders_are_idempotent(self):
        IncidentAssignment.objects.filter(pk=self.assignment.pk).update(
            created_at=timezone.now() - timedelta(days=15)
        )

        call_command("remind_overdue_cases", stdout=StringIO())
        call_command("remind_overdue_cases", stdout=StringIO())

        self.assertEqual(
            Notification.objects.filter(
                incident=self.incident,
                title="Case unresolved for 14 days",
            ).count(),
            2,
        )
