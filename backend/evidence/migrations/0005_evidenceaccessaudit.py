import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("evidence", "0004_evidence_sha256_hash_type"),
        ("incidents", "0006_incidentassignment_unique_active_incident_assignment_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="EvidenceAccessAudit",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("action", models.CharField(choices=[("viewed", "Evidence viewed"), ("audio_accessed", "Audio accessed"), ("downloaded", "Evidence downloaded"), ("verified", "Evidence verification performed"), ("access_denied", "Access denied")], max_length=24)),
                ("occurred_at", models.DateTimeField(auto_now_add=True)),
                ("outcome", models.CharField(choices=[("success", "Success"), ("denied", "Denied")], max_length=12)),
                ("request_id", models.CharField(blank=True, max_length=128)),
                ("evidence", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="access_audit_events", to="evidence.evidence")),
                ("incident", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="incidents.incident")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="evidence_access_audit_events", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-occurred_at"]},
        ),
    ]
