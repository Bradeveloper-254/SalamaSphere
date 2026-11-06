import hashlib
import logging
import uuid

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from evidence.crypto import encrypt_evidence
from evidence.models import Evidence


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Encrypt existing plaintext evidence files at rest."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report how many legacy files would be encrypted.",
        )

    def handle(self, *args, **options):
        legacy_items = Evidence.objects.filter(encryption_version=0)
        if options["dry_run"]:
            self.stdout.write(
                f"{legacy_items.count()} legacy evidence file(s) found."
            )
            return

        encrypted_count = 0
        for evidence in legacy_items.iterator():
            saved_key = None
            try:
                with default_storage.open(evidence.storage_key, "rb") as file:
                    plaintext = file.read()

                plaintext_hash = hashlib.sha256(plaintext).hexdigest()
                if (
                    evidence.sha256_hash
                    and evidence.sha256_hash != plaintext_hash
                ):
                    raise CommandError(
                        f"Evidence {evidence.pk} does not match its stored "
                        "SHA-256 hash; refusing to re-encrypt it."
                    )

                new_key = f"evidence/encrypted/{uuid.uuid4()}.bin"
                encrypted_data = encrypt_evidence(plaintext, evidence.pk)
                saved_key = default_storage.save(
                    new_key,
                    ContentFile(encrypted_data),
                )
                old_key = evidence.storage_key

                try:
                    with transaction.atomic():
                        locked_evidence = Evidence.objects.select_for_update().get(
                            pk=evidence.pk,
                        )
                        if locked_evidence.encryption_version != 0:
                            default_storage.delete(saved_key)
                            continue

                        locked_evidence.storage_key = saved_key
                        locked_evidence.sha256_hash = plaintext_hash
                        locked_evidence.encryption_version = 1
                        locked_evidence.save(
                            update_fields=[
                                "storage_key",
                                "sha256_hash",
                                "encryption_version",
                            ]
                        )
                except Exception:
                    default_storage.delete(saved_key)
                    raise

                try:
                    default_storage.delete(old_key)
                except Exception as exc:
                    logger.exception(
                        "Could not delete the plaintext legacy evidence file "
                        "for evidence %s.",
                        evidence.pk,
                    )
                    raise CommandError(
                        f"Evidence {evidence.pk} was encrypted, but its "
                        "legacy plaintext file could not be deleted."
                    ) from exc

                encrypted_count += 1
                self.stdout.write(f"Encrypted evidence {evidence.pk}.")
            except CommandError:
                raise
            except Exception as exc:
                if saved_key:
                    try:
                        default_storage.delete(saved_key)
                    except Exception:
                        logger.exception(
                            "Could not remove incomplete encrypted evidence "
                            "for evidence %s.",
                            evidence.pk,
                        )
                raise CommandError(
                    f"Could not encrypt evidence {evidence.pk}."
                ) from exc

        self.stdout.write(
            self.style.SUCCESS(
                f"Encrypted {encrypted_count} legacy evidence file(s)."
            )
        )
