from django.test import TestCase
from rest_framework.test import APIClient
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.test import APIClient

from .models import AuthorityVerificationDocument
from .models import User


class UserModelTests(TestCase):
    def test_user_can_be_created(self):
        user = User.objects.create_user(
            username="test_survivor",
            email="survivor@example.com",
            password="TestPassword123!",
        )

        self.assertEqual(user.username, "test_survivor")
        self.assertEqual(user.role, User.Role.SURVIVOR)
        self.assertTrue(user.check_password("TestPassword123!"))


class AuthorityDocumentPermissionTests(TestCase):
    DOCUMENT_LIST_URL = "/api/accounts/admin/verification-documents/"

    def setUp(self):
        self.client = APIClient()

        self.survivor = User.objects.create_user(
            username="test_survivor_2",
            email="survivor2@example.com",
            password="TestPassword123!",
            role=User.Role.SURVIVOR,
        )

        self.authority = User.objects.create_user(
            username="test_authority",
            email="authority@example.com",
            password="TestPassword123!",
            role=User.Role.AUTHORITY,
            authority_status=User.AuthorityStatus.PENDING,
        )

        self.admin = User.objects.create_user(
            username="test_admin",
            email="admin@example.com",
            password="TestPassword123!",
            role=User.Role.ADMIN,
            is_staff=True,
        )

    def test_anonymous_user_cannot_list_documents(self):
        response = self.client.get(self.DOCUMENT_LIST_URL)

        self.assertIn(response.status_code, [401, 403])

    def test_survivor_cannot_list_documents(self):
        self.client.force_authenticate(user=self.survivor)

        response = self.client.get(self.DOCUMENT_LIST_URL)

        self.assertEqual(response.status_code, 403)

    def test_pending_authority_cannot_list_documents(self):
        self.client.force_authenticate(user=self.authority)

        response = self.client.get(self.DOCUMENT_LIST_URL)

        self.assertEqual(response.status_code, 403)

    def test_admin_can_list_documents(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.get(self.DOCUMENT_LIST_URL)

        self.assertEqual(response.status_code, 200)

@override_settings(
    MEDIA_ROOT=None,
)
class AuthorityDocumentReviewTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.authority = User.objects.create_user(
            username="review_authority",
            email="review_authority@example.com",
            password="TestPassword123!",
            role=User.Role.AUTHORITY,
            authority_status=User.AuthorityStatus.PENDING,
        )

        self.admin = User.objects.create_user(
            username="review_admin",
            email="review_admin@example.com",
            password="TestPassword123!",
            role=User.Role.ADMIN,
            is_staff=True,
        )

        self.survivor = User.objects.create_user(
            username="review_survivor",
            email="review_survivor@example.com",
            password="TestPassword123!",
            role=User.Role.SURVIVOR,
        )

        uploaded_file = SimpleUploadedFile(
            "test_document.pdf",
            b"%PDF-1.4\nTest document content",
            content_type="application/pdf",
        )

        self.document = AuthorityVerificationDocument.objects.create(
            authority=self.authority,
            document_type=(
                AuthorityVerificationDocument.DocumentType.NATIONAL_ID
            ),
            file=uploaded_file,
        )

        self.review_url = (
            f"/api/accounts/admin/verification-documents/"
            f"{self.document.id}/"
        )

    def test_admin_can_accept_pending_document(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            self.review_url,
            {"decision": "accepted", "reason": ""},
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        self.document.refresh_from_db()
        self.assertEqual(
            self.document.review_status,
            AuthorityVerificationDocument.ReviewStatus.ACCEPTED,
        )
        self.assertEqual(self.document.reviewer, self.admin)
        self.assertIsNotNone(self.document.reviewed_at)

    def test_admin_can_reject_document_with_reason(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            self.review_url,
            {
                "decision": "rejected",
                "reason": "The document could not be verified.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        self.document.refresh_from_db()
        self.assertEqual(
            self.document.review_status,
            AuthorityVerificationDocument.ReviewStatus.REJECTED,
        )
        self.assertEqual(
            self.document.review_reason,
            "The document could not be verified.",
        )

    def test_admin_cannot_reject_document_without_reason(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            self.review_url,
            {"decision": "rejected", "reason": ""},
            format="json",
        )

        self.assertEqual(response.status_code, 400)

        self.document.refresh_from_db()
        self.assertEqual(
            self.document.review_status,
            AuthorityVerificationDocument.ReviewStatus.PENDING,
        )

    def test_document_cannot_be_reviewed_twice(self):
        self.client.force_authenticate(user=self.admin)

        first_response = self.client.post(
            self.review_url,
            {"decision": "accepted", "reason": ""},
            format="json",
        )

        self.assertEqual(first_response.status_code, 200)

        second_response = self.client.post(
            self.review_url,
            {
                "decision": "rejected",
                "reason": "Attempted second review.",
            },
            format="json",
        )

        self.assertEqual(second_response.status_code, 409)

        self.document.refresh_from_db()
        self.assertEqual(
            self.document.review_status,
            AuthorityVerificationDocument.ReviewStatus.ACCEPTED,
        )

    def test_survivor_cannot_review_document(self):
        self.client.force_authenticate(user=self.survivor)

        response = self.client.post(
            self.review_url,
            {"decision": "accepted", "reason": ""},
            format="json",
        )

        self.assertEqual(response.status_code, 403)

    def test_pending_authority_cannot_review_document(self):
        self.client.force_authenticate(user=self.authority)

        response = self.client.post(
            self.review_url,
            {"decision": "accepted", "reason": ""},
            format="json",
        )

        self.assertEqual(response.status_code, 403)