from django.db import models

from django.conf import settings
from django.db import models


class TrustedContact(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="trusted_contacts",
    )

    name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=20)
    relationship = models.CharField(
        max_length=50,
        blank=True,
    )

    is_active = models.BooleanField(default=True)

    receive_sos_alerts = models.BooleanField(default=True)

    consent_confirmed = models.BooleanField(default=False)
    consent_confirmed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "phone_number"],
                name="unique_user_trusted_contact_phone",
            )
        ]

    def __str__(self):
        return f"{self.name} — user {self.user_id}"