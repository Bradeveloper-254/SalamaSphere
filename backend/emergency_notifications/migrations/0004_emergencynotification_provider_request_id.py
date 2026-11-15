from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        (
            "emergency_notifications",
            "0003_alter_emergencynotification_status",
        ),
    ]

    operations = [
        migrations.AddField(
            model_name="emergencynotification",
            name="provider_request_id",
            field=models.CharField(blank=True, db_index=True, max_length=150),
        ),
    ]
