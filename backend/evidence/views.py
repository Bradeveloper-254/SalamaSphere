import hashlib
import logging
import uuid
from pathlib import Path

from django.core.files.storage import default_storage
from django.db import transaction
from django.utils import timezone

from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from incidents.models import Incident

from .models import Evidence
from .serializers import EvidenceUploadSerializer


logger = logging.getLogger(__name__)


def user_can_access_incident(user, incident):
    return (
        incident.device_id is not None
        and incident.device.owner_id == user.id
    )


def calculate_sha256(file_obj):
    digest = hashlib.sha256()

    for chunk in file_obj.chunks():
        digest.update(chunk)

    return digest.hexdigest()


class EvidenceUploadView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, incident_id):
        incident = Incident.objects.filter(
            id=incident_id,
            device__owner=request.user,
        ).first()

        if incident is None:
            return Response(
                {"detail": "Incident not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = EvidenceUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        uploaded_file = serializer.validated_data["file"]
        evidence_type = serializer.validated_data["evidence_type"]
        recorded_at = serializer.validated_data.get("recorded_at")

        extension = Path(uploaded_file.name).suffix.lower()
        mime_type = (
            getattr(uploaded_file, "content_type", None)
            or "application/octet-stream"
        ).lower()

        storage_key = (
            f"evidence/{evidence_type}/{uuid.uuid4()}{extension}"
        )

        sha256_hash = calculate_sha256(uploaded_file)
        uploaded_file.seek(0)

        saved_key = None

        try:
            with transaction.atomic():
                saved_key = default_storage.save(
                    storage_key,
                    uploaded_file,
                )

                evidence = Evidence.objects.create(
                    incident=incident,
                    uploaded_by=request.user,
                    evidence_type=evidence_type,
                    original_filename=Path(
                        uploaded_file.name
                    ).name[:255],
                    storage_key=saved_key,
                    mime_type=mime_type,
                    file_size_bytes=uploaded_file.size,
                    sha256_hash=sha256_hash,
                    verification_status=(
                        Evidence.VerificationStatus.PENDING
                    ),
                    recorded_at=recorded_at,
                )

        except Exception as exc:
            if saved_key:
                try:
                    default_storage.delete(saved_key)
                except Exception:
                    logger.exception(
                        "Failed to clean up uploaded evidence."
                    )

            logger.exception(
                "Evidence upload failed for incident %s",
                incident.id,
            )
            raise APIException(
                "Evidence could not be stored."
            ) from exc

        return Response(
            {
                "message": "Evidence uploaded successfully.",
                "evidence_id": str(evidence.id),
                "incident_id": str(incident.id),
                "evidence_type": evidence.evidence_type,
                "original_filename": evidence.original_filename,
                "storage_key": evidence.storage_key,
                "mime_type": evidence.mime_type,
                "file_size_bytes": evidence.file_size_bytes,
                "sha256_hash": evidence.sha256_hash,
                "verification_status": evidence.verification_status,
                "uploaded_at": evidence.uploaded_at,
            },
            status=status.HTTP_201_CREATED,
        )


class EvidenceVerificationView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, incident_id):
        incident = Incident.objects.filter(
            id=incident_id,
            device__owner=request.user,
        ).first()

        if incident is None:
            return Response(
                {"detail": "Incident not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        evidence_items = Evidence.objects.filter(
            incident=incident
        )

        if not evidence_items.exists():
            return Response(
                {"detail": "No evidence exists for this incident."},
                status=status.HTTP_404_NOT_FOUND,
            )

        results = []

        for evidence in evidence_items:
            now = timezone.now()

            try:
                with default_storage.open(
                    evidence.storage_key,
                    "rb",
                ) as stored_file:
                    digest = hashlib.sha256()

                    for chunk in iter(
                        lambda: stored_file.read(1024 * 1024),
                        b"",
                    ):
                        digest.update(chunk)

                current_hash = digest.hexdigest()
                matches = current_hash == evidence.sha256_hash

                evidence.verification_status = (
                    Evidence.VerificationStatus.VERIFIED
                    if matches
                    else Evidence.VerificationStatus.MISMATCH
                )

                evidence.last_verified_at = now
                evidence.save(
                    update_fields=[
                        "verification_status",
                        "last_verified_at",
                    ]
                )

                results.append({
                    "evidence_id": str(evidence.id),
                    "evidence_type": evidence.evidence_type,
                    "original_sha256": evidence.sha256_hash,
                    "current_sha256": current_hash,
                    "matches": matches,
                    "verification_status": evidence.verification_status,
                    "verified_at": now,
                })

            except FileNotFoundError:
                evidence.verification_status = (
                    Evidence.VerificationStatus.FAILED
                )
                evidence.last_verified_at = now
                evidence.save(
                    update_fields=[
                        "verification_status",
                        "last_verified_at",
                    ]
                )

                results.append({
                    "evidence_id": str(evidence.id),
                    "evidence_type": evidence.evidence_type,
                    "verification_status": "failed",
                    "matches": False,
                    "verified_at": now,
                })

            except Exception:
                logger.exception(
                    "Verification failed for evidence %s",
                    evidence.id,
                )

                evidence.verification_status = (
                    Evidence.VerificationStatus.FAILED
                )
                evidence.last_verified_at = now
                evidence.save(
                    update_fields=[
                        "verification_status",
                        "last_verified_at",
                    ]
                )

                results.append({
                    "evidence_id": str(evidence.id),
                    "evidence_type": evidence.evidence_type,
                    "verification_status": "failed",
                    "matches": False,
                    "verified_at": now,
                })

        all_verified = all(
            item["verification_status"] == "verified"
            for item in results
        )

        return Response(
            {
                "incident_id": str(incident.id),
                "verified": all_verified,
                "evidence_count": len(results),
                "results": results,
                "message": (
                    "All evidence files match their recorded hashes."
                    if all_verified
                    else "One or more evidence files failed verification."
                ),
            },
            status=status.HTTP_200_OK,
        )