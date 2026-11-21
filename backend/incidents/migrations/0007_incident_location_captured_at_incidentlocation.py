# Historical duplicate of 0007_incident_location_history.  Keep its migration
# name for deployments that have recorded it, but make it a no-op so a fresh
# database does not attempt to create the location table twice.
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('incidents', '0007_incident_location_history'),
    ]

    operations = []
