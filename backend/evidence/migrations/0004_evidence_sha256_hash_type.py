from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("evidence", "0003_evidence_encryption_version")]

    operations = [
        migrations.AddField(
            model_name="evidence",
            name="sha256_hash_type",
            field=models.CharField(default="plaintext", max_length=32),
        ),
    ]
