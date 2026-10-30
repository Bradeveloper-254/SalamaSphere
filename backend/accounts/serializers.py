from django.contrib.auth import password_validation
from django.contrib.auth.models import update_last_login
from django.db import transaction
from rest_framework import serializers

from .models import User
from pathlib import Path

from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import FileExtensionValidator
from rest_framework.exceptions import ValidationError

class RegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
        style={"input_type": "password"},
    )

    role = serializers.ChoiceField(
        choices=[
            (User.Role.SURVIVOR, "Survivor"),
            (User.Role.AUTHORITY, "Authority"),
        ],
        default=User.Role.SURVIVOR,
    )

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "password",
            "phone_number",
            "role",
        ]

    def validate_password(self, value):
        password_validation.validate_password(value)
        return value

    @transaction.atomic
    def create(self, validated_data):
        role = validated_data.pop("role", User.Role.SURVIVOR)

        authority_status = (
            User.AuthorityStatus.PENDING
            if role == User.Role.AUTHORITY
            else User.AuthorityStatus.NOT_APPLICABLE
        )

        user = User(
            **validated_data,
            role=role,
            authority_status=authority_status,
            is_active=True,
        )

        user.set_password(validated_data["password"])
        user.save()

        return user
    
from .models import AuthorityVerificationDocument


class AuthorityVerificationDocumentSerializer(serializers.ModelSerializer):
    file = serializers.FileField(
        validators=[
            FileExtensionValidator(
                allowed_extensions=["pdf", "jpg", "jpeg", "png"]
            )
        ]
    )

    class Meta:
        model = AuthorityVerificationDocument
        fields = [
            "id",
            "document_type",
            "file",
            "review_status",
            "submitted_at",
        ]
        read_only_fields = [
            "id",
            "review_status",
            "submitted_at",
        ]

    def validate_file(self, uploaded_file):
        max_size = 5 * 1024 * 1024

        if uploaded_file.size > max_size:
            raise ValidationError(
                "The document must not exceed 5 MB."
            )

        extension = Path(uploaded_file.name).suffix.lower()

        allowed_content_types = {
            ".pdf": {"application/pdf"},
            ".jpg": {"image/jpeg"},
            ".jpeg": {"image/jpeg"},
            ".png": {"image/png"},
        }

        if extension not in allowed_content_types:
            raise ValidationError(
                "Only PDF, JPG, JPEG, and PNG files are allowed."
            )

        content_type = getattr(
            uploaded_file,
            "content_type",
            None,
        )

        if content_type not in allowed_content_types[extension]:
            raise ValidationError(
                "The uploaded file's declared content type does not "
                "match an allowed format."
            )

        return uploaded_file

    def validate(self, attrs):
        request = self.context.get("request")

        if request is None or not request.user.is_authenticated:
            raise ValidationError(
                "Authentication is required."
            )

        user = request.user

        if user.role != User.Role.AUTHORITY:
            raise ValidationError(
                "Only authority applicants may submit verification documents."
            )

        if user.authority_status != User.AuthorityStatus.PENDING:
            raise ValidationError(
                "Documents can only be submitted while your authority "
                "application is pending."
            )

        return attrs
    
class AuthorityDocumentReviewSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(
        choices=[
            ("accepted", "Accepted"),
            ("rejected", "Rejected"),
        ]
    )

    reason = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=2000,
    )

    def validate(self, attrs):
        decision = attrs["decision"]
        reason = attrs.get("reason", "").strip()

        if decision == "rejected" and not reason:
            raise serializers.ValidationError({
                "reason": "A reason is required when rejecting a document."
            })

        attrs["reason"] = reason
        return attrs