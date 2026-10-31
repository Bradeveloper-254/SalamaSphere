from django.http import JsonResponse
from django.db import connection


def health_check(request):
    try:
        # Check whether Django can reach its configured database.
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()

        return JsonResponse({
            "status": "healthy",
            "database": "connected",
            "service": "SalamaSphere API",
        })

    except Exception:
        return JsonResponse({
            "status": "degraded",
            "database": "unavailable",
            "service": "SalamaSphere API",
        }, status=503)