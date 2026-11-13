from django.db.models import Count, Q
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from devices.models import WearableDevice
from incidents.models import Incident


class DashboardOverviewView(APIView):
    """Return the data needed by each role's navigation shell."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if user.role == User.Role.AUTHORITY:
            incidents = Incident.objects.filter(
                authority_assignments__authority=user,
                authority_assignments__is_active=True,
            ).distinct()
        elif user.is_superuser or (
            user.role == User.Role.ADMIN
            and user.is_staff
            and user.is_active
        ):
            incidents = Incident.objects.all()
        else:
            incidents = Incident.objects.filter(user=user)

        summary = incidents.aggregate(
            total=Count("id"),
            urgent=Count("id", filter=Q(threat_level="high") | Q(is_sos=True)),
            open=Count("id", filter=Q(status__in=["pending", "received"])),
            reviewed=Count("id", filter=Q(status="reviewed")),
        )

        incident_rows = []
        for incident in incidents.select_related("device").prefetch_related(
            "evidence_files"
        ).order_by("-received_at")[:20]:
            incident_rows.append({
                "id": str(incident.id),
                "client_event_id": (
                    str(incident.client_event_id)
                    if incident.client_event_id
                    else None
                ),
                "threat_level": incident.threat_level,
                "status": incident.status,
                "source": incident.source,
                "description": incident.description,
                "is_sos": incident.is_sos,
                "occurred_at": incident.occurred_at,
                "received_at": incident.received_at,
                "latitude": incident.latitude,
                "longitude": incident.longitude,
                "location_map_url": incident.location_map_url,
                "location_accuracy_m": incident.location_accuracy_m,
                "location_source": incident.location_source,
                "audio_available": any(
                    item.evidence_type == "audio"
                    for item in incident.evidence_files.all()
                ),
                "evidence": [
                    {
                        "id": str(evidence.id),
                        "evidence_type": evidence.evidence_type,
                        "original_filename": evidence.original_filename,
                        "mime_type": evidence.mime_type,
                        "file_size_bytes": evidence.file_size_bytes,
                        "uploaded_at": evidence.uploaded_at,
                        "file_url": f"/api/evidence/{evidence.id}/file/",
                        "metadata": evidence.metadata,
                    }
                    for evidence in incident.evidence_files.all()
                ] if incident.user_id == user.id else [],
            })

        return Response({
            "role": user.role,
            "summary": summary,
            "incidents": incident_rows,
            "devices": list(WearableDevice.objects.filter(owner=user).values(
                "id", "device_name", "device_identifier", "status", "last_seen_at",
            )),
        })


class AdminSettingsOverviewView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not (request.user.is_superuser or (
            request.user.is_staff and request.user.role == User.Role.ADMIN
        )):
            return Response({"detail": "Administrator access is required."}, status=403)

        return Response({
            "user_statistics": {
                "total": User.objects.count(),
                "survivors": User.objects.filter(role=User.Role.SURVIVOR).count(),
                "authorities_pending": User.objects.filter(
                    role=User.Role.AUTHORITY,
                    authority_status=User.AuthorityStatus.PENDING,
                ).count(),
            },
            "device_status": {
                "active": WearableDevice.objects.filter(status="active").count(),
                "inactive": WearableDevice.objects.filter(status="inactive").count(),
                "revoked": WearableDevice.objects.filter(status="revoked").count(),
            },
            "sync_queue": Incident.objects.filter(
                sync_received_at__isnull=True,
            ).count(),
        })
