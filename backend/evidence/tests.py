import hashlib
from pathlib import Path
import tempfile
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files.storage import default_storage
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from incidents.models import Incident
from dashboard.models import IncidentAuditEvent
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
        self.assertEqual(evidence.encryption_version, 1)
        self.assertEqual(
            evidence.sha256_hash,
            hashlib.sha256(b"video-data").hexdigest(),
        )
        with default_storage.open(evidence.storage_key, "rb") as stored:
            self.assertNotEqual(stored.read(), b"video-data")
        self.assertTrue(
            IncidentAuditEvent.objects.filter(
                incident=self.incident,
                action=IncidentAuditEvent.Action.EVIDENCE_UPLOADED,
                outcome=IncidentAuditEvent.Outcome.SUCCESS,
            ).exists()
        )

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

        verification = self.client.get(
            reverse(
                "evidence-verify",
                kwargs={"incident_id": self.incident.id},
            )
        )
        self.assertEqual(verification.status_code, 200)
        self.assertTrue(verification.data["verified"])

    def test_tampered_encrypted_file_is_not_returned(self):
        response = self.client.post(
            self.upload_url,
            {
                "file": SimpleUploadedFile(
                    "incident.mp4",
                    b"video-data",
                    content_type="video/mp4",
                ),
                "share_with": "authorities",
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 201, response.data)
        evidence = Evidence.objects.get(incident=self.incident)
        stored_path = Path(self.media_directory.name) / evidence.storage_key
        with stored_path.open("r+b") as stored:
            stored.seek(-1, 2)
            final_byte = stored.read(1)
            stored.seek(-1, 2)
            stored.write(bytes([final_byte[0] ^ 1]))

        file_response = self.client.get(
            reverse(
                "evidence-file",
                kwargs={"evidence_id": evidence.id},
            )
        )

        self.assertEqual(file_response.status_code, 409)
        evidence.refresh_from_db()
        self.assertEqual(
            evidence.verification_status,
            Evidence.VerificationStatus.MISMATCH,
        )

    def test_management_command_encrypts_legacy_plaintext_evidence(self):
        response = self.client.post(
            self.upload_url,
            {
                "file": SimpleUploadedFile(
                    "incident.mp4",
                    b"legacy-video-data",
                    content_type="video/mp4",
                ),
                "share_with": "authorities",
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 201, response.data)
        evidence = Evidence.objects.get(incident=self.incident)
        default_storage.delete(evidence.storage_key)
        default_storage.save(
            evidence.storage_key,
            ContentFile(b"legacy-video-data"),
        )
        evidence.encryption_version = 0
        evidence.save(update_fields=["encryption_version"])

        call_command("encrypt_legacy_evidence")

        evidence.refresh_from_db()
        self.assertEqual(evidence.encryption_version, 1)
        with default_storage.open(evidence.storage_key, "rb") as stored:
            self.assertNotEqual(stored.read(), b"legacy-video-data")
        file_response = self.client.get(
            reverse(
                "evidence-file",
                kwargs={"evidence_id": evidence.id},
            )
        )
        self.assertEqual(file_response.status_code, 200)
        self.assertEqual(
            b"".join(file_response.streaming_content),
            b"legacy-video-data",
        )

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
