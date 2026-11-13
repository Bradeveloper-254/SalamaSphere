from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import User
from .models import WearableDevice


class DeviceRegistrationAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="device_owner",
            email="device_owner@example.com",
            password="TestPassword123!",
        )
        self.client.force_authenticate(user=self.user)
        self.endpoint = reverse("device-register")
        self.payload = {
            "device_name": "SalamaSphere wearable",
            "device_identifier": "SALAMA-CLAIM-001",
            "firmware_version": "unknown",
        }

    def test_registration_creates_active_device_for_current_user(self):
        response = self.client.post(
            self.endpoint,
            self.payload,
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.data)
        device = WearableDevice.objects.get(
            device_identifier=self.payload["device_identifier"],
        )
        self.assertEqual(device.owner, self.user)
        self.assertEqual(device.status, WearableDevice.DeviceStatus.ACTIVE)

    def test_registration_is_idempotent_for_same_active_owner(self):
        device = WearableDevice.objects.create(
            owner=self.user,
            device_name="Existing wearable",
            device_identifier=self.payload["device_identifier"],
        )

        response = self.client.post(
            self.endpoint,
            self.payload,
            format="json",
        )

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["id"], str(device.pk))
        self.assertEqual(WearableDevice.objects.count(), 1)

    def test_registration_cannot_claim_another_users_device(self):
        other_user = User.objects.create_user(
            username="other_device_owner",
            email="other_device_owner@example.com",
            password="TestPassword123!",
        )
        device = WearableDevice.objects.create(
            owner=other_user,
            device_name="Other wearable",
            device_identifier=self.payload["device_identifier"],
        )

        response = self.client.post(
            self.endpoint,
            self.payload,
            format="json",
        )

        self.assertEqual(response.status_code, 409)
        device.refresh_from_db()
        self.assertEqual(device.owner, other_user)
        self.assertEqual(WearableDevice.objects.count(), 1)

    def test_registration_does_not_reactivate_inactive_device(self):
        device = WearableDevice.objects.create(
            owner=self.user,
            device_name="Inactive wearable",
            device_identifier=self.payload["device_identifier"],
            status=WearableDevice.DeviceStatus.INACTIVE,
        )

        response = self.client.post(
            self.endpoint,
            self.payload,
            format="json",
        )

        self.assertEqual(response.status_code, 409)
        device.refresh_from_db()
        self.assertEqual(device.status, WearableDevice.DeviceStatus.INACTIVE)
