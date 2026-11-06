import base64
import hashlib
import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


_FORMAT_HEADER = b"SS-EVIDENCE\x01"
_NONCE_LENGTH = 12


def _encryption_key():
    configured_key = settings.EVIDENCE_ENCRYPTION_KEY
    if configured_key:
        try:
            key = base64.urlsafe_b64decode(configured_key.encode("ascii"))
        except (ValueError, UnicodeEncodeError) as exc:
            raise ImproperlyConfigured(
                "EVIDENCE_ENCRYPTION_KEY must be URL-safe base64."
            ) from exc

        if len(key) != 32:
            raise ImproperlyConfigured(
                "EVIDENCE_ENCRYPTION_KEY must decode to exactly 32 bytes."
            )
        return key

    return hashlib.sha256(
        settings.SECRET_KEY.encode("utf-8")
        + b":salamasphere:evidence-encryption:v1"
    ).digest()


def encrypt_evidence(plaintext, evidence_id):
    nonce = os.urandom(_NONCE_LENGTH)
    associated_data = f"salamasphere:evidence:v1:{evidence_id}".encode()
    ciphertext = AESGCM(_encryption_key()).encrypt(
        nonce,
        plaintext,
        associated_data,
    )
    return _FORMAT_HEADER + nonce + ciphertext


def decrypt_evidence(stored_data, evidence_id, encryption_version):
    if encryption_version == 0:
        return stored_data
    if encryption_version != 1 or not stored_data.startswith(_FORMAT_HEADER):
        raise ValueError("Unsupported or invalid evidence encryption format.")

    nonce_start = len(_FORMAT_HEADER)
    nonce_end = nonce_start + _NONCE_LENGTH
    if len(stored_data) <= nonce_end:
        raise ValueError("Encrypted evidence is incomplete.")

    associated_data = f"salamasphere:evidence:v1:{evidence_id}".encode()
    try:
        return AESGCM(_encryption_key()).decrypt(
            stored_data[nonce_start:nonce_end],
            stored_data[nonce_end:],
            associated_data,
        )
    except InvalidTag as exc:
        raise ValueError(
            "Evidence authentication failed; stored data may be corrupted."
        ) from exc
