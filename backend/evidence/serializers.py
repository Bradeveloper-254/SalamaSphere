from pathlib import Path

from rest_framework import serializers

from .models import Evidence


MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MiB

ALLOWED_FILES = {
    ".wav": ("audio", {"audio/wav", "audio/x-wav"}),
    ".mp3": ("audio", {"audio/mpeg", "audio/mp3"}),
    ".m4a": ("audio", {"audio/mp4", "audio/x-m4a", "application/octet-stream"}),
    ".aac": ("audio", {"audio/aac", "application/octet-stream"}),
    ".ogg": ("audio", {"audio/ogg", "application/ogg"}),
    ".webm": ("audio", {"audio/webm", "application/octet-stream"}),
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

        supplied_type = attrs.get("evidence_type")

        if supplied_type and supplied_type != detected_type:
            raise serializers.ValidationError({
                "evidence_type": (
                    "The evidence type does not match the file extension."
                )
            })

        attrs["evidence_type"] = supplied_type or detected_type
        return attrs