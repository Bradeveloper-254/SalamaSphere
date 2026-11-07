import hashlib
import hmac
import io
import logging
import uuid
from pathlib import Path

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import transaction
from django.db.models import Q
from django.http import FileResponse
from django.utils import timezone

from dashboard.audit import record_incident_audit
from dashboard.models import IncidentAuditEvent

from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from incidents.models import Incident
from notifications.services import create_system_notification

from .crypto import decrypt_evidence, encrypt_evidence
from .models import Evidence
from .serializers import EvidenceUploadSerializer


logger = logging.getLogger(__name__)


class EvidenceIntegrityError(Exception):
    pass


def calculate_sha256(file_obj):
    digest = hashlib.sha256()

    for chunk in file_obj.chunks():
        digest.update(chunk)

    return digest.hexdigest()


def load_evidence(evidence):
    try:
        with default_storage.open(evidence.storage_key, "rb") as stored_file:
            stored_data = stored_file.read()
    except FileNotFoundError:
        raise

    try:
        plaintext = decrypt_evidence(
            stored_data,
            evidence.id,
            evidence.encryption_version,
        )
    except ValueError as exc:
        raise EvidenceIntegrityError from exc

    return plaintext, hashlib.sha256(plaintext).hexdigest()


def mark_evidence_verified(evidence, matches):
    evidence.verification_status = (
        Evidence.VerificationStatus.VERIFIED
        if matches
        else Evidence.VerificationStatus.MISMATCH
    )
    evidence.last_verified_at = timezone.now()
    evidence.save(
        update_fields=[
            "verification_status",
            "last_verified_at",
        ]
    )


class EvidenceUploadView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_incident(self, request, incident_id):
        return Incident.objects.filter(id=incident_id).filter(
            Q(user=request.user) | Q(device__owner=request.user)
        ).first()

    def get(self, request, incident_id):
        incident = self.get_incident(request, incident_id)
        if incident is None:
            return Response(
                {"detail": "Incident not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response([
            {
                "id": str(item.id),
                "evidence_type": item.evidence_type,
                "original_filename": item.original_filename,
                "mime_type": item.mime_type,
                "file_size_bytes": item.file_size_bytes,
                "verification_status": item.verification_status,
                "encrypted_at_rest": item.encryption_version > 0,
                "uploaded_at": item.uploaded_at,
                "file_url": f"/api/evidence/{item.id}/file/",
                "metadata": item.metadata,
            }
            for item in Evidence.objects.filter(incident=incident)
        ])

    def post(self, request, incident_id):
        incident = self.get_incident(request, incident_id)

        if incident is None:
            return Response(
                {"detail": "Incident not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = EvidenceUploadSerializer(
            data=request.data,
            context={"request": request},
        )
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
        evidence_id = uuid.uuid4()

        saved_key = None

        try:
            encrypted_data = encrypt_evidence(
                uploaded_file.read(),
                evidence_id,
            )
            with transaction.atomic():
                saved_key = default_storage.save(
                    storage_key,
                    ContentFile(encrypted_data),
                )

                evidence = Evidence.objects.create(
                    id=evidence_id,
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
                    encryption_version=1,
                    verification_status=(
                        Evidence.VerificationStatus.PENDING
                    ),
                    recorded_at=recorded_at,
                    metadata={
                        "share_with": serializer.validated_data["share_with"],
                        "trusted_contact_ids": serializer.validated_data[
                            "trusted_contact_ids"
                        ],
                    },
                )
                record_incident_audit(
                    actor=request.user,
                    incident=incident,
                    action=IncidentAuditEvent.Action.EVIDENCE_UPLOADED,
                    outcome=IncidentAuditEvent.Outcome.SUCCESS,
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

        create_system_notification(
            recipient=incident.user,
            incident=incident,
            title="Evidence shared successfully",
            message=(
                f"Your {evidence.get_evidence_type_display().lower()} "
                f"file, {evidence.original_filename}, was uploaded "
                "successfully and attached to your incident."
            ),
        )

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
                "encrypted_at_rest": evidence.encryption_version > 0,
                "verification_status": evidence.verification_status,
                "uploaded_at": evidence.uploaded_at,
            },
            status=status.HTTP_201_CREATED,
        )


class EvidenceAudioView(EvidenceUploadView):
    """Upload or stream the WAV evidence attached to an incident."""

    def _get_incident(self, request, incident_id):
        return self.get_incident(request, incident_id)

    def get(self, request, incident_id):
        incident = self._get_incident(request, incident_id)
        if incident is None:
            return Response(
                {"detail": "Incident not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        evidence = Evidence.objects.filter(
            incident=incident,
            evidence_type=Evidence.EvidenceType.AUDIO,
        ).order_by("-uploaded_at").first()
        if evidence is None:
            return Response(
                {"detail": "No audio evidence exists for this incident."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            plaintext, current_hash = load_evidence(evidence)
        except FileNotFoundError:
            return Response(
                {"detail": "The stored audio file is unavailable."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except EvidenceIntegrityError:
            mark_evidence_verified(evidence, matches=False)
            record_incident_audit(
                actor=request.user,
                incident=incident,
                action=IncidentAuditEvent.Action.EVIDENCE_ACCESSED,
                outcome=IncidentAuditEvent.Outcome.FAILURE,
            )
            return Response(
                {"detail": "Evidence integrity verification failed."},
                status=status.HTTP_409_CONFLICT,
            )

        if not hmac.compare_digest(evidence.sha256_hash, current_hash):
            mark_evidence_verified(evidence, matches=False)
            record_incident_audit(
                actor=request.user,
                incident=incident,
                action=IncidentAuditEvent.Action.EVIDENCE_ACCESSED,
                outcome=IncidentAuditEvent.Outcome.FAILURE,
            )
            return Response(
                {"detail": "Evidence integrity verification failed."},
                status=status.HTTP_409_CONFLICT,
            )

        mark_evidence_verified(evidence, matches=True)
        record_incident_audit(
            actor=request.user,
            incident=incident,
            action=IncidentAuditEvent.Action.EVIDENCE_ACCESSED,
            outcome=IncidentAuditEvent.Outcome.SUCCESS,
        )

        response = FileResponse(
            io.BytesIO(plaintext),
            content_type=evidence.mime_type or "audio/wav",
        )
        response["Content-Length"] = str(evidence.file_size_bytes)
        response["Content-Disposition"] = (
            f'inline; filename="{evidence.original_filename}"'
        )
        response["X-Evidence-Id"] = str(evidence.id)
        response["X-Evidence-SHA256"] = evidence.sha256_hash
        return response


class EvidenceVerificationView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, incident_id):
        incident = Incident.objects.filter(id=incident_id).filter(
            Q(user=request.user) | Q(device__owner=request.user)
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
                _, current_hash = load_evidence(evidence)
                matches = bool(evidence.sha256_hash) and hmac.compare_digest(
                    current_hash,
                    evidence.sha256_hash,
                )
                mark_evidence_verified(evidence, matches)

                results.append({
                    "evidence_id": str(evidence.id),
                    "evidence_type": evidence.evidence_type,
                    "original_sha256": evidence.sha256_hash,
                    "current_sha256": current_hash,
                    "matches": matches,
                    "verification_status": evidence.verification_status,
                    "verified_at": now,
                })

            except EvidenceIntegrityError:
                evidence.verification_status = (
                    Evidence.VerificationStatus.MISMATCH
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
                    "verification_status": "mismatch",
                    "matches": False,
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

        record_incident_audit(
            actor=request.user,
            incident=incident,
            action=IncidentAuditEvent.Action.EVIDENCE_VERIFICATION,
            outcome=(
                IncidentAuditEvent.Outcome.SUCCESS
                if all_verified
                else IncidentAuditEvent.Outcome.FAILURE
            ),
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
                    else (
                        "One or more evidence files failed verification."
                    )
                ),
            },
            status=status.HTTP_200_OK,
        )


class EvidenceFileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, evidence_id):
        evidence = Evidence.objects.filter(
            id=evidence_id,
            incident__user=request.user,
        ).first()
        if evidence is None:
            evidence = Evidence.objects.filter(
                id=evidence_id,
                incident__device__owner=request.user,
            ).first()
        if evidence is None:
            return Response(
                {"detail": "Evidence file not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            plaintext, current_hash = load_evidence(evidence)
        except FileNotFoundError:
            return Response(
                {"detail": "The stored evidence file is unavailable."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except EvidenceIntegrityError:
            mark_evidence_verified(evidence, matches=False)
            record_incident_audit(
                actor=request.user,
                incident=evidence.incident,
                action=IncidentAuditEvent.Action.EVIDENCE_ACCESSED,
                outcome=IncidentAuditEvent.Outcome.FAILURE,
            )
            return Response(
                {"detail": "Evidence integrity verification failed."},
                status=status.HTTP_409_CONFLICT,
            )

        if not hmac.compare_digest(evidence.sha256_hash, current_hash):
            mark_evidence_verified(evidence, matches=False)
            record_incident_audit(
                actor=request.user,
                incident=evidence.incident,
                action=IncidentAuditEvent.Action.EVIDENCE_ACCESSED,
                outcome=IncidentAuditEvent.Outcome.FAILURE,
            )
            return Response(
                {"detail": "Evidence integrity verification failed."},
                status=status.HTTP_409_CONFLICT,
            )

        mark_evidence_verified(evidence, matches=True)
        record_incident_audit(
            actor=request.user,
            incident=evidence.incident,
            action=IncidentAuditEvent.Action.EVIDENCE_ACCESSED,
            outcome=IncidentAuditEvent.Outcome.SUCCESS,
        )

        response = FileResponse(
            io.BytesIO(plaintext),
            content_type=evidence.mime_type or "application/octet-stream",
        )
        response["Content-Length"] = str(evidence.file_size_bytes)
        response["Content-Disposition"] = (
            f'inline; filename="{evidence.original_filename}"'
        )
        response["X-Evidence-SHA256"] = evidence.sha256_hash
        return response
