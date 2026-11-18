from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("evidence", "0006_evidencetranscript"),
    ]

    operations = [
        migrations.AlterField(
            model_name="evidenceaccessaudit",
            name="user",
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                related_name="evidence_access_audit_events", to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="evidencetranscript", name="reviewed_transcript",
            field=models.TextField(blank=True),
        ),
        migrations.CreateModel(
            name="EvidenceTranscriptRevision",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("text", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("reviewer", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
                ("transcript_record", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="revisions", to="evidence.evidencetranscript")),
            ],
            options={"ordering": ["created_at"]},
        ),
    ]
