import hashlib
import html
import hmac
import io
import logging
import uuid
from pathlib import Path

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core import signing
from django.db import transaction
from django.db.models import Q
from django.http import FileResponse, HttpResponse, HttpResponseNotFound
from django.urls import reverse
from django.utils import timezone
from django.utils.text import get_valid_filename

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
from trusted_contacts.models import TrustedContact

from emergency_notifications.message_builder import (
    ACCESS_LINK_MAX_AGE_SECONDS,
    ACCESS_LINK_SALT,
)
from emergency_notifications.services import (
    process_pending_emergency_notifications,
)

from .crypto import decrypt_evidence, encrypt_evidence
from .models import Evidence, EvidenceAccessAudit, EvidenceTranscript, EvidenceTranscriptRevision
from .serializers import EvidenceUploadSerializer, EvidenceTranscriptionSerializer
from .transcription import OpenAITranscriptionProvider, TranscriptionError


logger = logging.getLogger(__name__)


def audit_evidence_access(request, incident, action, outcome, evidence=None):
    request_id = (
        request.headers.get("X-Request-ID")
        or request.headers.get("X-Correlation-ID")
        or ""
    )[:128]
    EvidenceAccessAudit.objects.create(
        incident=incident,
        evidence=evidence,
        user=(request.user if getattr(request.user, "is_authenticated", False) else None),
        action=action,
        outcome=outcome,
        request_id=request_id,
    )


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
            denied_incident = Incident.objects.filter(pk=incident_id).first()
            if denied_incident is not None:
                audit_evidence_access(
                    request, denied_incident, EvidenceAccessAudit.Action.ACCESS_DENIED,
                    EvidenceAccessAudit.Outcome.DENIED,
                )
            return Response(
                {"detail": "Incident not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        items = list(Evidence.objects.filter(incident=incident))
        for item in items:
            audit_evidence_access(
                request, incident, EvidenceAccessAudit.Action.VIEWED,
                EvidenceAccessAudit.Outcome.SUCCESS, item,
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
            for item in items
        ])

    def post(self, request, incident_id):
        incident = self.get_incident(request, incident_id)

        if incident is None:
            denied_incident = Incident.objects.filter(pk=incident_id).first()
            if denied_incident is not None:
                audit_evidence_access(
                    request, denied_incident, EvidenceAccessAudit.Action.ACCESS_DENIED,
                    EvidenceAccessAudit.Outcome.DENIED,
                )
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
        expected_hash = serializer.validated_data.get("sha256_hash")
        hash_type = serializer.validated_data["sha256_hash_type"]

        extension = Path(uploaded_file.name).suffix.lower()
        mime_type = (
            getattr(uploaded_file, "content_type", None)
            or "application/octet-stream"
        ).lower()

        storage_key = (
            f"evidence/{evidence_type}/{uuid.uuid4()}{extension}"
        )

        sha256_hash = calculate_sha256(uploaded_file)
        if expected_hash and not hmac.compare_digest(sha256_hash, expected_hash.lower()):
            return Response(
                {"verification_status": "VERIFICATION_FAILED",
                 "detail": "Uploaded bytes do not match the original SHA-256 hash."},
                status=status.HTTP_400_BAD_REQUEST,
            )
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
                    sha256_hash_type=hash_type,
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
                "sha256_hash_type": evidence.sha256_hash_type,
                "encrypted_at_rest": evidence.encryption_version > 0,
                "verification_status": evidence.verification_status,
                "uploaded_at": evidence.uploaded_at,
            },
            status=status.HTTP_201_CREATED,
        )


class EvidenceAudioView(EvidenceUploadView):
    """Upload or stream the WAV evidence attached to an incident."""

    def _get_incident(self, request, incident_id):
        user = request.user
        incident = Incident.objects.filter(pk=incident_id).first()
        if incident is None:
            return None

        owns_incident = (
            incident.user_id == user.pk
            or incident.device is not None
            and incident.device.owner_id == user.pk
        )
        is_admin = user.is_active and (
            user.is_superuser
            or user.is_staff and getattr(user, "role", None) == "admin"
        )
        is_assigned_authority = (
            user.is_active
            and getattr(user, "role", None) == "authority"
            and getattr(user, "authority_status", None) == "approved"
            and incident.authority_assignments.filter(
                authority=user,
                is_active=True,
            ).exists()
        )
        return (
            incident
            if owns_incident or is_admin or is_assigned_authority
            else None
        )

    def get(self, request, incident_id):
        incident = self._get_incident(request, incident_id)
        if incident is None:
            denied_incident = Incident.objects.filter(pk=incident_id).first()
            if denied_incident is not None:
                audit_evidence_access(
                    request, denied_incident, EvidenceAccessAudit.Action.ACCESS_DENIED,
                    EvidenceAccessAudit.Outcome.DENIED,
                )
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
            audit_evidence_access(
                request, incident, EvidenceAccessAudit.Action.AUDIO_ACCESSED,
                EvidenceAccessAudit.Outcome.DENIED, evidence,
            )
            return Response(
                {"detail": "Evidence integrity verification failed."},
                status=status.HTTP_409_CONFLICT,
            )

        if not hmac.compare_digest(evidence.sha256_hash, current_hash):
            mark_evidence_verified(evidence, matches=False)
            audit_evidence_access(
                request, incident, EvidenceAccessAudit.Action.AUDIO_ACCESSED,
                EvidenceAccessAudit.Outcome.DENIED, evidence,
            )
            return Response(
                {"detail": "Evidence integrity verification failed."},
                status=status.HTTP_409_CONFLICT,
            )

        mark_evidence_verified(evidence, matches=True)
        audit_evidence_access(
            request, incident, EvidenceAccessAudit.Action.AUDIO_ACCESSED,
            EvidenceAccessAudit.Outcome.SUCCESS, evidence,
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


class EmergencyIncidentLinkView(APIView):
    """Time-limited, recipient-specific audio and location link from an SOS SMS."""

    authentication_classes = []
    permission_classes = []

    def _get_access(self, token):
        try:
            payload = signing.loads(
                token,
                salt=ACCESS_LINK_SALT,
                max_age=ACCESS_LINK_MAX_AGE_SECONDS,
            )
        except signing.BadSignature:
            return None

        incident = Incident.objects.filter(
            pk=payload.get("incident_id"),
        ).select_related("user").first()
        if incident is None:
            return None
        contact = TrustedContact.objects.filter(
            pk=payload.get("contact_id"),
            user_id=incident.user_id,
            is_active=True,
            receive_sos_alerts=True,
            consent_confirmed=True,
        ).first()
        if contact is None:
            return None
        evidence = Evidence.objects.filter(
            incident=incident,
            evidence_type=Evidence.EvidenceType.AUDIO,
        ).order_by("-uploaded_at").first()
        if evidence is None:
            return None
        return incident, evidence

    def get(self, request, token):
        access = self._get_access(token)
        if access is None:
            return HttpResponseNotFound(
                "This private incident link is invalid or has expired."
            )
        incident, evidence = access
        audio_url = reverse(
            "emergency-incident-audio",
            kwargs={"token": token},
        )
        map_link = incident.location_map_url
        location_html = (
            f'<a href="{html.escape(map_link, quote=True)}" '
            'rel="noopener noreferrer">Open incident location in Google Maps</a>'
            if map_link
            else "Location is unavailable."
        )
        username = html.escape(incident.user.username)
        filename = html.escape(evidence.original_filename)
        mime_type = html.escape(evidence.mime_type or "audio/wav", quote=True)
        page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="referrer" content="no-referrer">
<title>SalamaSphere emergency incident</title>
</head>
<body>
<main>
<h1>SalamaSphere emergency incident</h1>
<p>{username} may be in danger or under threat. Please help them as soon as possible.</p>
<p>{location_html}</p>
<h2>Recorded audio</h2>
<audio controls preload="none"><source src="{html.escape(audio_url, quote=True)}" type="{mime_type}"></audio>
<p><a href="{html.escape(audio_url, quote=True)}?download=1" download="{filename}">Download recorded audio</a></p>
<p>This private link expires in 7 days.</p>
</main>
</body>
</html>"""
        response = HttpResponse(page, content_type="text/html; charset=utf-8")
        response["Cache-Control"] = "private, no-store"
        response["Referrer-Policy"] = "no-referrer"
        response["X-Content-Type-Options"] = "nosniff"
        response["Content-Security-Policy"] = (
            "default-src 'none'; media-src 'self'; style-src 'unsafe-inline'; "
            "base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
        )
        return response

    def audio(self, request, token):
        access = self._get_access(token)
        if access is None:
            return HttpResponseNotFound(
                "This private incident link is invalid or has expired."
            )
        incident, evidence = access
        action = (
            EvidenceAccessAudit.Action.DOWNLOADED
            if request.GET.get("download") == "1"
            else EvidenceAccessAudit.Action.AUDIO_ACCESSED
        )
        try:
            plaintext, current_hash = load_evidence(evidence)
        except FileNotFoundError:
            return HttpResponseNotFound("The recorded audio is unavailable.")
        except EvidenceIntegrityError:
            mark_evidence_verified(evidence, matches=False)
            audit_evidence_access(
                request, incident, action, EvidenceAccessAudit.Outcome.DENIED,
                evidence,
            )
            return HttpResponse(
                "Audio integrity verification failed.",
                status=status.HTTP_409_CONFLICT,
            )

        if not hmac.compare_digest(evidence.sha256_hash, current_hash):
            mark_evidence_verified(evidence, matches=False)
            audit_evidence_access(
                request, incident, action, EvidenceAccessAudit.Outcome.DENIED,
                evidence,
            )
            return HttpResponse(
                "Audio integrity verification failed.",
                status=status.HTTP_409_CONFLICT,
            )

        mark_evidence_verified(evidence, matches=True)
        audit_evidence_access(
            request, incident, action, EvidenceAccessAudit.Outcome.SUCCESS,
            evidence,
        )
        filename = get_valid_filename(evidence.original_filename)
        disposition = (
            "attachment"
            if request.GET.get("download") == "1"
            else "inline"
        )
        response = FileResponse(
            io.BytesIO(plaintext),
            content_type=evidence.mime_type or "audio/wav",
        )
        response["Content-Length"] = str(evidence.file_size_bytes)
        response["Content-Disposition"] = (
            f'{disposition}; filename="{filename}"'
        )
        response["Cache-Control"] = "private, no-store"
        response["Referrer-Policy"] = "no-referrer"
        response["X-Content-Type-Options"] = "nosniff"
        response["X-Evidence-SHA256"] = evidence.sha256_hash
        return response


class EmergencyIncidentAudioLinkView(EmergencyIncidentLinkView):
    def get(self, request, token):
        return self.audio(request, token)


class EvidenceVerificationView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, incident_id):
        incident = Incident.objects.filter(id=incident_id).filter(
            Q(user=request.user) | Q(device__owner=request.user)
        ).first()

        if incident is None:
            denied_incident = Incident.objects.filter(pk=incident_id).first()
            if denied_incident is not None:
                audit_evidence_access(
                    request, denied_incident,
                    EvidenceAccessAudit.Action.ACCESS_DENIED,
                    EvidenceAccessAudit.Outcome.DENIED,
                )
            return Response(
                {"detail": "Incident not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        evidence_items = Evidence.objects.filter(
            incident=incident
        )
        evidence_items = list(evidence_items)

        if not evidence_items:
            audit_evidence_access(
                request, incident, EvidenceAccessAudit.Action.VERIFIED,
                EvidenceAccessAudit.Outcome.SUCCESS,
            )
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
                    "verification_status": (
                        "VERIFIED" if matches else "VERIFICATION_FAILED"
                    ),
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
        for evidence in evidence_items:
            result = next(
                item for item in results
                if item["evidence_id"] == str(evidence.id)
            )
            audit_evidence_access(
                request, incident, EvidenceAccessAudit.Action.VERIFIED,
                (EvidenceAccessAudit.Outcome.SUCCESS if result["matches"]
                 else EvidenceAccessAudit.Outcome.DENIED), evidence,
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
            candidate = Evidence.objects.filter(pk=evidence_id).select_related(
                "incident"
            ).first()
            if candidate is not None:
                audit_evidence_access(
                    request, candidate.incident,
                    EvidenceAccessAudit.Action.ACCESS_DENIED,
                    EvidenceAccessAudit.Outcome.DENIED, candidate,
                )
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
            audit_evidence_access(
                request, evidence.incident, EvidenceAccessAudit.Action.DOWNLOADED,
                EvidenceAccessAudit.Outcome.DENIED, evidence,
            )
            return Response(
                {"detail": "Evidence integrity verification failed."},
                status=status.HTTP_409_CONFLICT,
            )

        if not hmac.compare_digest(evidence.sha256_hash, current_hash):
            mark_evidence_verified(evidence, matches=False)
            audit_evidence_access(
                request, evidence.incident, EvidenceAccessAudit.Action.DOWNLOADED,
                EvidenceAccessAudit.Outcome.DENIED, evidence,
            )
            return Response(
                {"detail": "Evidence integrity verification failed."},
                status=status.HTTP_409_CONFLICT,
            )

        mark_evidence_verified(evidence, matches=True)
        audit_evidence_access(
            request, evidence.incident,
            EvidenceAccessAudit.Action.DOWNLOADED,
            EvidenceAccessAudit.Outcome.SUCCESS, evidence,
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


class EvidenceTranscriptionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, evidence_id):
        evidence = Evidence.objects.filter(pk=evidence_id).filter(
            Q(incident__user=request.user)
            | Q(incident__device__owner=request.user)
        ).first()
        if evidence is None:
            candidate = Evidence.objects.filter(pk=evidence_id).select_related(
                "incident"
            ).first()
            if candidate:
                audit_evidence_access(
                    request, candidate.incident,
                    EvidenceAccessAudit.Action.ACCESS_DENIED,
                    EvidenceAccessAudit.Outcome.DENIED, candidate,
                )
            return Response({"detail": "Evidence file not found."}, status=404)
        if evidence.evidence_type != Evidence.EvidenceType.AUDIO:
            return Response({"detail": "Only audio evidence can be transcribed."}, status=400)

        serializer = EvidenceTranscriptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        requested_language = serializer.validated_data["language"]
        transcript_record = EvidenceTranscript.objects.create(
            evidence=evidence,
            incident=evidence.incident,
            language=requested_language if requested_language != "auto" else "und",
            language_source=(
                EvidenceTranscript.LanguageSource.USER_SELECTED
                if requested_language != "auto"
                else EvidenceTranscript.LanguageSource.AUTOMATIC
            ),
            status=EvidenceTranscript.Status.PROCESSING,
            created_by=request.user,
        )
        try:
            audio, current_hash = load_evidence(evidence)
            if not hmac.compare_digest(evidence.sha256_hash, current_hash):
                raise TranscriptionError("evidence_integrity_failed")
            language = None if requested_language == "auto" else requested_language
            text, detected_language = OpenAITranscriptionProvider().transcribe(
                audio,
                evidence.original_filename,
                evidence.mime_type or "application/octet-stream",
                language,
            )
            transcript_record.language = (
                detected_language or "und" if requested_language == "auto" else requested_language
            )
            transcript_record.transcript = text
            transcript_record.status = EvidenceTranscript.Status.COMPLETED
            transcript_record.processed_at = timezone.now()
            transcript_record.save(update_fields=[
                "language", "transcript", "status", "processed_at",
            ])
            audit_evidence_access(
                request, evidence.incident, EvidenceAccessAudit.Action.AUDIO_ACCESSED,
                EvidenceAccessAudit.Outcome.SUCCESS, evidence,
            )
            return Response({
                "transcript_id": transcript_record.pk,
                "evidence_id": str(evidence.pk),
                "incident_id": str(evidence.incident_id),
                "language": transcript_record.language if transcript_record.language != "und" else None,
                "language_source": transcript_record.language_source,
                "processed_at": transcript_record.processed_at,
                "status": transcript_record.status,
                "transcript": text,
                "human_review_required": True,
            }, status=201)
        except FileNotFoundError:
            error_code = "evidence_unavailable"
        except TranscriptionError as exc:
            error_code = exc.code
        except Exception:
            logger.error("Speech transcription failed (unexpected processing error).")
            error_code = "processing_failed"

        transcript_record.status = EvidenceTranscript.Status.FAILED
        transcript_record.error_code = error_code
        transcript_record.processed_at = timezone.now()
        transcript_record.save(update_fields=["status", "error_code", "processed_at"])
        audit_evidence_access(
            request, evidence.incident, EvidenceAccessAudit.Action.AUDIO_ACCESSED,
            EvidenceAccessAudit.Outcome.DENIED, evidence,
        )
        return Response({
            "transcript_id": transcript_record.pk,
            "status": transcript_record.status,
            "error": "Speech recognition could not process this audio. Please try another recording or language setting.",
            "error_code": error_code,
            "human_review_required": True,
        }, status=422)


def owned_transcript_evidence(user, evidence_id):
    return Evidence.objects.filter(pk=evidence_id).filter(
        Q(incident__user=user) | Q(incident__device__owner=user)
    ).first()


class EvidenceTranscriptListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, evidence_id):
        evidence = owned_transcript_evidence(request.user, evidence_id)
        if evidence is None:
            return Response({"detail": "Evidence file not found."}, status=404)
        rows = evidence.transcripts.all()
        return Response([{
            "transcript_id": item.pk,
            "status": item.status,
            "language": item.language if item.language != "und" else None,
            "language_source": item.language_source,
            "transcript": item.transcript,
            "reviewed_transcript": item.reviewed_transcript or None,
            "human_review_required": item.human_review_required,
            "processed_at": item.processed_at,
            "reviewed_at": item.reviewed_at,
            "history": [{"text": rev.text, "reviewer_id": rev.reviewer_id,
                         "created_at": rev.created_at} for rev in item.revisions.all()],
        } for item in rows])


class EvidenceTranscriptReviewView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, transcript_id):
        item = EvidenceTranscript.objects.filter(pk=transcript_id).filter(
            Q(incident__user=request.user) | Q(incident__device__owner=request.user)
        ).first()
        if item is None:
            return Response({"detail": "Transcript not found."}, status=404)
        text = request.data.get("transcript")
        if not isinstance(text, str) or not text.strip():
            return Response({"transcript": ["A corrected transcript is required."]}, status=400)
        corrected = text.strip()
        EvidenceTranscriptRevision.objects.create(
            transcript_record=item, text=corrected, reviewer=request.user,
        )
        item.reviewed_transcript = corrected
        item.reviewed_by = request.user
        item.reviewed_at = timezone.now()
        item.save(update_fields=["reviewed_transcript", "reviewed_by", "reviewed_at"])
        return Response({"transcript_id": item.pk, "transcript": item.transcript,
                         "reviewed_transcript": corrected,
                         "reviewed_at": item.reviewed_at})
