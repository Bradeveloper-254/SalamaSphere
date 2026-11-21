import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("incidents", "0007_incident_location_history"),
        ("incidents", "0007_incident_location_captured_at_incidentlocation"),
    ]

    operations = [
        migrations.CreateModel(
            name="LiveAudioSession",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ("victim_consent", models.BooleanField(default=False)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("active", "Active"), ("terminated", "Terminated"), ("expired", "Expired")], default="pending", max_length=16)),
                ("expires_at", models.DateTimeField()),
                ("terminated_at", models.DateTimeField(blank=True, null=True)),
                ("victim_token_hash", models.CharField(max_length=64)),
                ("responder_token_hash", models.CharField(max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("incident", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="live_audio_sessions", to="incidents.incident")),
                ("responder", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="responder_live_audio_sessions", to=settings.AUTH_USER_MODEL)),
                ("victim", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="live_audio_sessions", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="LiveAudioSignal",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ("sequence", models.PositiveIntegerField()),
                ("kind", models.CharField(max_length=16)),
                ("payload", models.JSONField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("sender", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
                ("session", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="signals", to="incidents.liveaudiosession")),
            ],
            options={"ordering": ["created_at"]},
        ),
        migrations.AddIndex(model_name="liveaudiosession", index=models.Index(fields=["incident", "status", "expires_at"], name="incidents_l_inciden_b15014_idx")),
        migrations.AddConstraint(model_name="liveaudiosignal", constraint=models.UniqueConstraint(fields=("session", "sender", "sequence"), name="unique_live_audio_signal_sequence")),
    ]
