from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User, AuthorityVerificationDocument

@admin.register(User)
class CustomUserAdmin(UserAdmin):

    list_display = (
        "username",
        "email",
        "role",
        "authority_status",
        "is_active",
        "is_staff",
    )

    list_filter = (
        "role",
        "authority_status",
        "is_active",
        "is_staff",
        "is_email_verified",
    )

    search_fields = (
        "username",
        "email",
        "phone_number",
    )

    fieldsets = UserAdmin.fieldsets + (
        (
            "SalamaSphere Information",
            {
                "fields": (
                    "role",
                    "phone_number",
                    "is_email_verified",
                    "authority_status",
                )
            },
        ),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        (
            "SalamaSphere Information",
            {
                "fields": (
                    "email",
                    "role",
                    "phone_number",
                    "authority_status",
                )
            },
        ),
    )

@admin.register(AuthorityVerificationDocument)
class AuthorityVerificationDocumentAdmin(admin.ModelAdmin):

    list_display = (
        "authority",
        "document_type",
        "review_status",
        "submitted_at",
        "reviewer",
        "reviewed_at",
    )

    list_filter = (
        "document_type",
        "review_status",
        "submitted_at",
    )

    search_fields = (
        "authority__username",
        "authority__email",
    )

    readonly_fields = (
        "submitted_at",
        "reviewed_at",
    )