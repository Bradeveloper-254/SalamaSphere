import uuid

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("incidents", "0006_incidentassignment_unique_active_incident_assignment_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="incident",
            name="location_captured_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name="IncidentLocation",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("client_location_id", models.UUIDField()),
                ("latitude", models.DecimalField(decimal_places=6, max_digits=9)),
                ("longitude", models.DecimalField(decimal_places=6, max_digits=9)),
                ("accuracy_m", models.FloatField(blank=True, null=True)),
                ("captured_at", models.DateTimeField()),
                ("speed_mps", models.FloatField(blank=True, null=True)),
                ("bearing_degrees", models.FloatField(blank=True, null=True)),
                ("source", models.CharField(default="phone_gps", max_length=30)),
                ("received_at", models.DateTimeField(auto_now_add=True)),
                ("incident", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="location_history", to="incidents.incident")),
            ],
            options={
                "ordering": ["-captured_at", "-received_at"],
                "indexes": [models.Index(fields=["incident", "-captured_at"], name="incident_loc_time_idx")],
                "constraints": [models.UniqueConstraint(fields=("incident", "client_location_id"), name="unique_incident_client_location")],
            },
        ),
    ]
