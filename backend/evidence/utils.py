import hashlib


def calculate_sha256(file_path):
    """
    Calculate the SHA-256 digest of a file.

    Returns:
        A 64-character hexadecimal digest.
    """

    digest = hashlib.sha256()

    with open(file_path, "rb") as audio:
        for chunk in iter(
            lambda: audio.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()