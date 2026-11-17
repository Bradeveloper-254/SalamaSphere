import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("evidence", "0005_evidenceaccessaudit"),
        ("incidents", "0006_incidentassignment_unique_active_incident_assignment_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="EvidenceTranscript",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("language", models.CharField(max_length=16)),
                ("language_source", models.CharField(choices=[("automatic", "Automatic detection"), ("user_selected", "User selected")], max_length=20)),
                ("transcript", models.TextField(blank=True)),
                ("status", models.CharField(choices=[("processing", "Processing"), ("completed", "Completed"), ("failed", "Failed")], max_length=16)),
                ("error_code", models.CharField(blank=True, max_length=64)),
                ("processed_at", models.DateTimeField(blank=True, null=True)),
                ("human_review_required", models.BooleanField(default=True)),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="requested_evidence_transcripts", to=settings.AUTH_USER_MODEL)),
                ("evidence", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="transcripts", to="evidence.evidence")),
                ("incident", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="evidence_transcripts", to="incidents.incident")),
                ("reviewed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="reviewed_evidence_transcripts", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-processed_at"]},
        ),
    ]
