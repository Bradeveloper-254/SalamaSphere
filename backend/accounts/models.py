from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        SURVIVOR = "survivor", "Survivor"
        TRUSTED_CONTACT = "trusted_contact", "Trusted Contact"
        SUPPORT_WORKER = "support_worker", "Support Worker"
        ADMIN = "admin", "Administrator"

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

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return self.username