from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from emergency_notifications.models import EmergencyNotification
from incidents.models import Incident

from .models import TrustedContact


User = get_user_model()


class TrustedContactApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="trusted_contact_owner",
            email="trusted_contact_owner@example.test",
            password="test-password",
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.endpoint = reverse("trusted-contact-list-create")

    def test_created_contact_is_returned_to_its_owner(self):
        created = self.client.post(
            self.endpoint,
            {
                "name": "Safety contact",
                "phone_number": "+254700000000",
                "relationship": "Friend",
                "is_active": True,
                "receive_sos_alerts": True,
                "confirm_sos_consent": True,
            },
            format="json",
        )

        self.assertEqual(created.status_code, 201, created.data)
        self.assertEqual(TrustedContact.objects.filter(user=self.user).count(), 1)

        listed = self.client.get(self.endpoint)

        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.data), 1)
        self.assertEqual(listed.data[0]["id"], created.data["id"])
        self.assertEqual(listed.data[0]["name"], "Safety contact")

    def test_sos_contact_requires_explicit_consent(self):
        response = self.client.post(
            self.endpoint,
            {
                "name": "Safety contact",
                "phone_number": "+254700000000",
                "receive_sos_alerts": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(TrustedContact.objects.exists())

    def test_voice_calls_require_separate_explicit_consent(self):
        payload = {
            "name": "Safety contact",
            "phone_number": "+254700000000",
            "receive_sos_alerts": False,
            "receive_voice_calls": True,
        }

        rejected = self.client.post(
            self.endpoint,
            payload,
            format="json",
        )

        self.assertEqual(rejected.status_code, 400)
        self.assertFalse(TrustedContact.objects.exists())

        accepted = self.client.post(
            self.endpoint,
            {**payload, "confirm_voice_consent": True},
            format="json",
        )

        self.assertEqual(accepted.status_code, 201, accepted.data)
        self.assertTrue(accepted.data["receive_voice_calls"])
        self.assertFalse(accepted.data["receive_sos_alerts"])

    def test_enabling_voice_calls_on_existing_contact_requires_consent(self):
        contact = TrustedContact.objects.create(
            user=self.user,
            name="Safety contact",
            phone_number="+254700000000",
            receive_sos_alerts=False,
        )
        endpoint = reverse(
            "trusted-contact-detail",
            kwargs={"pk": contact.pk},
        )

        rejected = self.client.patch(
            endpoint,
            {"receive_voice_calls": True},
            format="json",
        )
        self.assertEqual(rejected.status_code, 400)

        accepted = self.client.patch(
            endpoint,
            {
                "receive_voice_calls": True,
                "confirm_voice_consent": True,
            },
            format="json",
        )
        self.assertEqual(accepted.status_code, 200, accepted.data)
        self.assertTrue(accepted.data["receive_voice_calls"])

    def test_deleting_contact_with_delivery_history_deactivates_it(self):
        created = self.client.post(
            self.endpoint,
            {
                "name": "Safety contact",
                "phone_number": "+254700000000",
                "receive_sos_alerts": True,
                "confirm_sos_consent": True,
            },
            format="json",
        )
        self.assertEqual(created.status_code, 201, created.data)
        contact = TrustedContact.objects.get(pk=created.data["id"])
        incident = Incident.objects.create(
            user=self.user,
            occurred_at=timezone.now(),
        )
        EmergencyNotification.objects.create(
            incident=incident,
            recipient=contact,
        )

        deleted = self.client.delete(
            reverse(
                "trusted-contact-detail",
                kwargs={"pk": contact.pk},
            )
        )

        self.assertEqual(deleted.status_code, 204)
        contact.refresh_from_db()
        self.assertFalse(contact.is_active)
        self.assertEqual(self.client.get(self.endpoint).data, [])
