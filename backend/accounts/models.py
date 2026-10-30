from django.contrib.auth.models import AbstractUser
from django.db import models
from .private_storage import PrivateVerificationStorage

class User(AbstractUser):

    class Role(models.TextChoices):
        SURVIVOR = "survivor", "Survivor"
        TRUSTED_CONTACT = "trusted_contact", "Trusted Contact"
        SUPPORT_WORKER = "support_worker", "Support Worker"
        AUTHORITY = "authority", "Authority"
        ADMIN = "admin", "Administrator"

    class AuthorityStatus(models.TextChoices):
        NOT_APPLICABLE = "not_applicable", "Not Applicable"
        PENDING = "pending", "Pending Verification"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    email = models.EmailField(unique=True)

    role = models.CharField(
        max_length=30,
        choices=Role.choices,
        default=Role.SURVIVOR,
    )

    phone_number = models.CharField(
        max_length=20,
        blank=True,
    )

    is_email_verified = models.BooleanField(
        default=False,
    )

    authority_status = models.CharField(
        max_length=20,
        choices=AuthorityStatus.choices,
        default=AuthorityStatus.NOT_APPLICABLE,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )



    def __str__(self):
        return self.username

class AuthorityApprovalLog(models.Model):
    class Decision(models.TextChoices):
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    authority = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="approval_history",
    )

    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="authority_reviews",
    )

    decision = models.CharField(
        max_length=10,
        choices=Decision.choices,
    )

    reason = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return (
            f"{self.authority.username}: "
            f"{self.decision} by {self.reviewed_by.username}"
        )

class AuthorityVerificationDocument(models.Model):

    class DocumentType(models.TextChoices):
        NATIONAL_ID = "national_id", "National ID"
        EMPLOYMENT_ID = "employment_id", "Employment ID"
        PROFESSIONAL_ID = "professional_id", "Professional ID"
        AUTHORIZATION_LETTER = "authorization_letter", "Authorization Letter"
        OTHER = "other", "Other"

    class ReviewStatus(models.TextChoices):
        PENDING = "pending", "Pending Review"
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Rejected"

    authority = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="verification_documents",
        limit_choices_to={"role": User.Role.AUTHORITY},
    )

    document_type = models.CharField(
        max_length=30,
        choices=DocumentType.choices,
    )

    # Store a private file reference, not a public URL.
    file = models.FileField(
        storage=PrivateVerificationStorage(),
        upload_to="authority_verification/",
    )

    review_status = models.CharField(
        max_length=20,
        choices=ReviewStatus.choices,
        default=ReviewStatus.PENDING,
    )

    reviewer = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="reviewed_verification_documents",
        null=True,
        blank=True,
    )

    review_reason = models.TextField(
        blank=True,
    )

    submitted_at = models.DateTimeField(
        auto_now_add=True,
    )

    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    def __str__(self):
        return (
            f"{self.authority.username} - "
            f"{self.get_document_type_display()} - "
            f"{self.review_status}"
        )
        
class AuthorityAccountStatusLog(models.Model):
    class Action(models.TextChoices):
        SUSPENDED = "suspended", "Suspended"
        REACTIVATED = "reactivated", "Reactivated"

    authority = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="account_status_history",
    )

    changed_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="authority_account_status_changes",
    )

    action = models.CharField(
        max_length=12,
        choices=Action.choices,
    )

    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return (
            f"{self.authority.username}: "
            f"{self.action} by {self.changed_by.username}"
        )