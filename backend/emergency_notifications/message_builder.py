def build_emergency_message(incident):
    reference = str(incident.id)[:8].upper()

    timestamp = incident.occurred_at.strftime(
        "%d %b %Y, %H:%M UTC"
    )

    return (
        "SALAMASPHERE SOS\n"
        f"Reference: {reference}\n"
        f"Time: {timestamp}\n"
        "An SOS event has been registered. "
        "Please contact the person safely using "
        "your previously agreed method. "
        "Follow your agreed emergency plan."
    )