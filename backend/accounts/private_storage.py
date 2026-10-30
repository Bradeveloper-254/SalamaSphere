from pathlib import Path

from django.conf import settings
from django.core.files.storage import FileSystemStorage


class PrivateVerificationStorage(FileSystemStorage):
    """
    Store verification documents in a directory that must not
    be served directly by the web server.
    """

    def __init__(self, *args, **kwargs):
        kwargs["location"] = (
            Path(settings.BASE_DIR) / "private_media"
        )
        kwargs["base_url"] = None

        super().__init__(*args, **kwargs)