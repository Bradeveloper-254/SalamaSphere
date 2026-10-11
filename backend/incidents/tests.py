from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from accounts.models import User
from .models import Incident


class IncidentModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="incident_test_user",
            email="incident@example.com",
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