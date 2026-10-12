from django.test import SimpleTestCase

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