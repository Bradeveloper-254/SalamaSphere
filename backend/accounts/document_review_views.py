from pathlib import Path

from django.db import transaction
from django.http import FileResponse
from django.utils import timezone

from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    AuthorityVerificationDocument,
    User,
)
from .permissions import IsSalamaSphereAdmin
from .serializers import AuthorityDocumentReviewSerializer


class AuthorityVerificationDocumentListView(APIView):
    permission_classes = [IsAuthenticated, IsSalamaSphereAdmin]

    def get(self, request):
        documents = (
            AuthorityVerificationDocument.objects
            .filter(
                authority__role=User.Role.AUTHORITY,
                authority__authority_status=User.AuthorityStatus.PENDING,
            )
            .select_related("authority", "reviewer")
            .order_by("submitted_at")
        )

        results = [
            {
                "id": document.id,
                "authority_id": document.authority_id,
                "username": document.authority.username,
                "email": document.authority.email,
                "document_type": document.document_type,
                "review_status": document.review_status,
                "submitted_at": document.submitted_at.isoformat(),
            }
            for document in documents
        ]

        return Response(results)


class AuthorityVerificationDocumentDetailView(APIView):
    permission_classes = [IsAuthenticated, IsSalamaSphereAdmin]

    def get_document(self, document_id):
        try:
            return AuthorityVerificationDocument.objects.select_related(
                "authority", "reviewer"
            ).get(pk=document_id)
        except AuthorityVerificationDocument.DoesNotExist:
            return None

    def get(self, request, document_id):
        document = self.get_document(document_id)

        if document is None:
            return Response(
                {"detail": "Verification document not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response({
            "id": document.id,
            "authority_id": document.authority_id,
            "username": document.authority.username,
            "email": document.authority.email,
            "document_type": document.document_type,
            "review_status": document.review_status,
            "review_reason": document.review_reason,
            "reviewer": (
                document.reviewer.username
                if document.reviewer else None
            ),
            "submitted_at": document.submitted_at.isoformat(),
            "reviewed_at": (
                document.reviewed_at.isoformat()
                if document.reviewed_at else None
            ),
        })

    @transaction.atomic
    def post(self, request, document_id):
        serializer = AuthorityDocumentReviewSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)

        try:
            document = (
                AuthorityVerificationDocument.objects
                .select_for_update()
                .get(pk=document_id)
            )
        except AuthorityVerificationDocument.DoesNotExist:
            return Response(
                {"detail": "Verification document not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if document.authority.authority_status != User.AuthorityStatus.PENDING:
            return Response(
                {
                    "detail": (
                        "This authority application is no longer pending."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        if document.review_status != (
            AuthorityVerificationDocument.ReviewStatus.PENDING
        ):
            return Response(
                {"detail": "This document has already been reviewed."},
                status=status.HTTP_409_CONFLICT,
            )

        decision = serializer.validated_data["decision"]
        reason = serializer.validated_data["reason"]

        document.review_status = decision
        document.review_reason = reason
        document.reviewer = request.user
        document.reviewed_at = timezone.now()

        document.save(update_fields=[
            "review_status",
            "review_reason",
            "reviewer",
            "reviewed_at",
        ])

        return Response({
            "message": "Verification document review recorded.",
            "document_id": document.id,
            "review_status": document.review_status,
            "reviewer": request.user.username,
            "reviewed_at": document.reviewed_at.isoformat(),
        })


class AuthorityVerificationDocumentDownloadView(APIView):
    permission_classes = [IsAuthenticated, IsSalamaSphereAdmin]

    def get(self, request, document_id):
        try:
            document = AuthorityVerificationDocument.objects.get(
                pk=document_id
            )
        except AuthorityVerificationDocument.DoesNotExist:
            return Response(
                {"detail": "Verification document not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not document.file:
            return Response(
                {"detail": "No file is associated with this document."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            file_handle = document.file.open("rb")
        except (OSError, ValueError):
            return Response(
                {"detail": "The stored document is unavailable."},
                status=status.HTTP_404_NOT_FOUND,
            )

        extension = Path(document.file.name).suffix.lower()

        content_types = {
            ".pdf": "application/pdf",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
        }

        response = FileResponse(
            file_handle,
            content_type=content_types.get(
                extension,
                "application/octet-stream",
            ),
        )

        # Force download rather than rendering potentially unsafe content
        # inline in the browser.
        response["Content-Disposition"] = (
            f'attachment; filename="verification-document-{document.id}"'
        )
        response["X-Content-Type-Options"] = "nosniff"
        response["Cache-Control"] = "private, no-store"

        return response