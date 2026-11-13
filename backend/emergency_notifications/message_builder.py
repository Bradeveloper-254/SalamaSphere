from urllib.parse import urljoin

from django.conf import settings
from django.core import signing
from django.urls import reverse

ACCESS_LINK_SALT = "emergency_notifications.trusted_contact_access"
ACCESS_LINK_MAX_AGE_SECONDS = 7 * 24 * 60 * 60


def build_emergency_access_url(incident, contact):
    base_url = settings.SALAMASPHERE_PUBLIC_BASE_URL.rstrip("/")
    if not base_url:
        raise ValueError(
            "SALAMASPHERE_PUBLIC_BASE_URL must be configured "
            "before sending emergency SMS messages."
        )

    token = signing.dumps(
        {
            "incident_id": str(incident.id),
            "contact_id": contact.pk,
        },
        salt=ACCESS_LINK_SALT,
        compress=True,
    )
    path = reverse("emergency-incident-link", kwargs={"token": token})
    return urljoin(f"{base_url}/", path.lstrip("/"))


def build_emergency_message(incident):
    timestamp = incident.occurred_at.strftime(
        "%d %b %Y, %H:%M UTC"
    )
    location = incident.location_map_url or "Unavailable"
    name = incident.user.get_full_name().strip() or incident.user.username

    return (
        "SALAMASPHERE EMERGENCY ALERT\n\n"
        f"{name} has triggered an SOS emergency alert.\n\n"
        f"Time: {timestamp}\n"
        f"Location: {location}\n"
        "\nPlease try to contact the user and provide assistance.\n\n"
        "This is an automated emergency notification."
    )