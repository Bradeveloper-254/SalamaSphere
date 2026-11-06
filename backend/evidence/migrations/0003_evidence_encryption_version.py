from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("evidence", "0002_alter_evidence_options_evidence_last_verified_at_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="evidence",
            name="encryption_version",
            field=models.PositiveSmallIntegerField(default=0),
        ),
    ]
