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
        elif user.role == User.Role.ADMIN or user.is_superuser:
            incidents = Incident.objects.all()
        else:
            incidents = Incident.objects.filter(user=user)

        summary = incidents.aggregate(
            total=Count("id"),
            urgent=Count("id", filter=Q(threat_level="high") | Q(is_sos=True)),
            open=Count("id", filter=Q(status__in=["pending", "received"])),
            reviewed=Count("id", filter=Q(status="reviewed")),
        )

        return Response({
            "role": user.role,
            "summary": summary,
            "incidents": list(incidents.order_by("-received_at").values(
                "id", "threat_level", "status", "source", "is_sos",
                "occurred_at", "received_at",
            )[:20]),
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
