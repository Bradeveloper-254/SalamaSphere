from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

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
