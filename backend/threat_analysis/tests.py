from django.test import SimpleTestCase
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from incidents.models import Incident

from .services import assess_incident


class ThreatAssessmentServiceTests(SimpleTestCase):

    def test_user_selected_level_takes_precedence(self):
        result = assess_incident(
            user_selected_level="high",
            indicators={
                "inappropriate_behavior": True,
            },
        )

        self.assertEqual(result["level"], "high")
        self.assertEqual(result["source"], "user_selected")

    def test_immediate_danger_returns_high(self):
        result = assess_incident(
            indicators={"immediate_danger": True}
        )

        self.assertEqual(result["level"], "high")

    def test_serious_threat_returns_high(self):
        result = assess_incident(
            indicators={"serious_threat": True}
        )

        self.assertEqual(result["level"], "high")

    def test_credible_threat_returns_medium(self):
        result = assess_incident(
            indicators={"credible_threat": True}
        )

        self.assertEqual(result["level"], "medium")

    def test_coercion_returns_medium(self):
        result = assess_incident(
            indicators={"coercion": True}
        )

        self.assertEqual(result["level"], "medium")

    def test_repeated_harassment_returns_medium(self):
        result = assess_incident(
            indicators={"repeated_harassment": True}
        )

        self.assertEqual(result["level"], "medium")

    def test_inappropriate_behavior_returns_low(self):
        result = assess_incident(
            indicators={"inappropriate_behavior": True}
        )

        self.assertEqual(result["level"], "low")

    def test_missing_indicators_remain_unclassified(self):
        result = assess_incident(indicators={})

        self.assertIsNone(result["level"])
        self.assertTrue(result["needs_review"])

    def test_invalid_level_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_incident(
                user_selected_level="urgent"
            )

    def test_false_indicator_does_not_trigger_high(self):
        result = assess_incident(
            indicators={"immediate_danger": False}
        )

        self.assertIsNone(result["level"])

    def test_keyword_match_escalates_but_never_downgrades_selected_level(self):
        result = assess_incident(
            user_selected_level="low",
            description="They threatened to kill me.",
        )

        self.assertEqual(result["level"], "high")
        self.assertEqual(result["suggested_level"], "high")
        self.assertEqual(result["source"], "rules")
        self.assertTrue(result["needs_review"])
        self.assertIn("threatened", result["keyword_matches"]["medium"])
        self.assertIn("kill me", result["keyword_matches"]["high"])


class ThreatAssessmentApiTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(
            username="threat_owner",
            email="threat_owner@example.test",
            password="test-password",
        )
        self.other_user = user_model.objects.create_user(
            username="threat_other",
            email="threat_other@example.test",
            password="test-password",
        )
        self.incident = Incident.objects.create(
            user=self.owner,
            source=Incident.IncidentSource.MOBILE,
            threat_level=Incident.ThreatLevel.LOW,
            description="They threatened to kill me.",
            occurred_at=timezone.now(),
        )
        self.client = APIClient()

    def test_owner_can_create_assessment_for_owned_incident(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            reverse(
                "threat-assessment-create",
                kwargs={"incident_id": self.incident.id},
            ),
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["final_level"], "high")
        self.incident.refresh_from_db()
        self.assertEqual(self.incident.threat_level, "high")

    def test_non_owner_cannot_create_assessment(self):
        self.client.force_authenticate(user=self.other_user)

        response = self.client.post(
            reverse(
                "threat-assessment-create",
                kwargs={"incident_id": self.incident.id},
            ),
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 404)