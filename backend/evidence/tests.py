import tempfile
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from incidents.models import Incident
from trusted_contacts.models import TrustedContact

from .models import Evidence


User = get_user_model()


class IncidentEvidenceApiTests(TestCase):
    def setUp(self):
        self.media_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.media_directory.cleanup)
        override = override_settings(MEDIA_ROOT=self.media_directory.name)
        override.enable()
        self.addCleanup(override.disable)

        self.user = User.objects.create_user(
            username="evidence_owner",
            email="evidence_owner@example.test",
            password="test-password",
        )
        self.other_user = User.objects.create_user(
            username="evidence_other",
            email="evidence_other@example.test",
            password="test-password",
        )
        self.incident = Incident.objects.create(
            user=self.user,
            source=Incident.IncidentSource.MOBILE,
            description="Uploaded video report",
            occurred_at=timezone.now() - timedelta(minutes=1),
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.upload_url = reverse(
            "evidence-upload",
            kwargs={"incident_id": self.incident.id},
        )

    def test_mobile_incident_owner_can_upload_list_and_view_video(self):
        response = self.client.post(
            self.upload_url,
            {
                "file": SimpleUploadedFile(
                    "incident.webm",
                    b"video-data",
                    content_type="video/webm",
                ),
                "share_with": "authorities",
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 201, response.data)
        evidence = Evidence.objects.get(incident=self.incident)
        self.assertEqual(evidence.evidence_type, Evidence.EvidenceType.VIDEO)

        listing = self.client.get(self.upload_url)
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(listing.data[0]["id"], str(evidence.id))

        file_response = self.client.get(
            reverse(
                "evidence-file",
                kwargs={"evidence_id": evidence.id},
            )
        )
        self.assertEqual(file_response.status_code, 200)
        self.assertEqual(b"".join(file_response.streaming_content), b"video-data")

    def test_upload_rejects_contacts_not_owned_by_the_user(self):
        contact = TrustedContact.objects.create(
            user=self.other_user,
            name="Other user's contact",
            phone_number="+254700000000",
        )

        response = self.client.post(
            self.upload_url,
            {
                "file": SimpleUploadedFile(
                    "incident.mp4",
                    b"video-data",
                    content_type="video/mp4",
                ),
                "share_with": "trusted_contacts",
                "trusted_contact_ids[0]": str(contact.id),
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(Evidence.objects.filter(incident=self.incident).exists())

    def test_selected_trusted_contact_is_saved_with_uploaded_evidence(self):
        contact = TrustedContact.objects.create(
            user=self.user,
            name="Trusted friend",
            phone_number="+254700000000",
            is_active=True,
        )

        response = self.client.post(
            self.upload_url,
            {
                "file": SimpleUploadedFile(
                    "incident.mp4",
                    b"video-data",
                    content_type="video/mp4",
                ),
                "share_with": "trusted_contacts",
                "trusted_contact_ids[0]": str(contact.id),
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 201, response.data)
        evidence = Evidence.objects.get(incident=self.incident)
        self.assertEqual(evidence.metadata["share_with"], "trusted_contacts")
        self.assertEqual(
            evidence.metadata["trusted_contact_ids"],
            [contact.id],
        )

    def test_other_user_cannot_list_or_view_incident_evidence(self):
        self.client.force_authenticate(user=self.other_user)

        response = self.client.get(self.upload_url)

        self.assertEqual(response.status_code, 404)
