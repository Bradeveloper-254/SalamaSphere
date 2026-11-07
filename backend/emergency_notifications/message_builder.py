def build_emergency_message(incident):
    reference = str(incident.id)[:8].upper()

    timestamp = incident.occurred_at.strftime(
        "%d %b %Y, %H:%M UTC"
    )
    location = (
        f"https://maps.google.com/?q={incident.latitude},{incident.longitude}"
        if incident.latitude is not None and incident.longitude is not None
        else "Unavailable"
    )

    return (
        "SALAMASPHERE SOS\n"
        f"Reference: {reference}\n"
        f"Time: {timestamp}\n"
        f"Threat severity: {incident.get_threat_level_display()}\n"
        f"Location: {location}\n"
        "An SOS event has been registered. "
        "Please contact the person safely using "
        "your previously agreed method. "
        "Follow your agreed emergency plan."
    )