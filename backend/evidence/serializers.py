from pathlib import Path

from rest_framework import serializers

from trusted_contacts.models import TrustedContact

from .models import Evidence


MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MiB

ALLOWED_FILES = {
    ".wav": ("audio", {"audio/wav", "audio/x-wav"}),
    ".mp3": ("audio", {"audio/mpeg", "audio/mp3"}),
    ".m4a": ("audio", {"audio/mp4", "audio/x-m4a", "application/octet-stream"}),
    ".aac": ("audio", {"audio/aac", "application/octet-stream"}),
    ".ogg": ("audio", {"audio/ogg", "application/ogg"}),
    ".webm": ("audio", {"audio/webm", "application/octet-stream"}),
    ".amr": ("audio", {"audio/amr", "application/octet-stream"}),
    ".jpg": ("image", {"image/jpeg"}),
    ".jpeg": ("image", {"image/jpeg"}),
    ".png": ("image", {"image/png"}),
    ".webp": ("image", {"image/webp"}),
    ".mp4": ("video", {"video/mp4", "application/octet-stream"}),
    ".mov": ("video", {"video/quicktime", "application/octet-stream"}),
    ".pdf": ("document", {"application/pdf"}),
    ".txt": ("document", {"text/plain"}),
    ".docx": ("document", {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/octet-stream",
    }),
}


class EvidenceUploadSerializer(serializers.Serializer):
    file = serializers.FileField(write_only=True)
    evidence_type = serializers.ChoiceField(
        choices=Evidence.EvidenceType.choices,
        required=False,
    )
    recorded_at = serializers.DateTimeField(
        required=False,
        allow_null=True,
    )
    share_with = serializers.ChoiceField(
        choices=("authorities", "trusted_contacts", "both"),
        required=False,
        default="authorities",
    )
    trusted_contact_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        default=list,
    )

    def validate_file(self, uploaded_file):
        if uploaded_file.size == 0:
            raise serializers.ValidationError(
                "The uploaded file is empty."
            )

        if uploaded_file.size > MAX_FILE_SIZE:
            raise serializers.ValidationError(
                "Files must not exceed 20 MiB."
            )

        extension = Path(uploaded_file.name).suffix.lower()

        if extension not in ALLOWED_FILES:
            raise serializers.ValidationError(
                "Unsupported file extension."
            )

        reported_type = (
            getattr(uploaded_file, "content_type", None)
            or "application/octet-stream"
        ).lower()

        _, permitted_types = ALLOWED_FILES[extension]
        if extension == ".webm":
            permitted_types = {"audio/webm", "video/webm"}

        if reported_type not in permitted_types:
            raise serializers.ValidationError(
                "The reported content type does not match "
                "the permitted file format."
            )

        return uploaded_file

    def validate(self, attrs):
        uploaded_file = attrs["file"]
        extension = Path(uploaded_file.name).suffix.lower()
        detected_type, _ = ALLOWED_FILES[extension]
        if extension == ".webm":
            mime_type = (
                getattr(uploaded_file, "content_type", "") or ""
            ).lower()
            detected_type = (
                Evidence.EvidenceType.VIDEO
                if mime_type.startswith("video/")
                else Evidence.EvidenceType.AUDIO
            )

        supplied_type = attrs.get("evidence_type")

        if supplied_type and supplied_type != detected_type:
            raise serializers.ValidationError({
                "evidence_type": (
                    "The evidence type does not match the file extension."
                )
            })

        attrs["evidence_type"] = supplied_type or detected_type

        if attrs["share_with"] in {"trusted_contacts", "both"}:
            contact_ids = attrs["trusted_contact_ids"]
            if not contact_ids:
                raise serializers.ValidationError({
                    "trusted_contact_ids": (
                        "Select at least one trusted contact to share with."
                    )
                })
            contacts = TrustedContact.objects.filter(
                user=self.context["request"].user,
                is_active=True,
                id__in=contact_ids,
            )
            if len(set(contact_ids)) != contacts.count():
                raise serializers.ValidationError({
                    "trusted_contact_ids": (
                        "Select active trusted contacts from your account."
                    )
                })
        elif attrs["trusted_contact_ids"]:
            raise serializers.ValidationError({
                "trusted_contact_ids": (
                    "Trusted contacts can only be selected when sharing "
                    "with trusted contacts."
                )
            })

        return attrs