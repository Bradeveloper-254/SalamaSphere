import hmac
from xml.sax.saxutils import escape

from django.conf import settings
from django.http import HttpResponse
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import EmergencyNotification
from .voice_services import (
    generate_emergency_voice_announcement,
    update_voice_call_from_callback,
)


class AfricasTalkingVoiceCallbackView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    parser_classes = [FormParser, JSONParser, MultiPartParser]

    def post(self, request):
        configured_token = settings.AT_VOICE_CALLBACK_TOKEN
        supplied_token = request.query_params.get("token", "")
        if not configured_token:
            return Response(
                {"detail": "Voice callbacks are not configured."},
                status=503,
            )
        if not hmac.compare_digest(
            supplied_token.encode("utf-8"),
            configured_token.encode("utf-8"),
        ):
            return Response({"detail": "Invalid callback token."}, status=403)

        payload = request.data
        session_id = str(payload.get("sessionId") or "").strip()
        if not session_id or len(session_id) > 150:
            return Response(
                {"detail": "A valid call sessionId is required."},
                status=400,
            )

        event_status = (
            payload.get("status")
            or payload.get("callStatus")
            or payload.get("call_status")
        )
        active = str(payload.get("isActive", "")).strip().lower()
        normalized_status = (
            str(event_status or "")
            .strip()
            .lower()
            .replace("_", " ")
            .replace("-", " ")
        )
        if (
            active in {"1", "true", "yes", "active"}
            and normalized_status
            not in {
                "completed",
                "complete",
                "ended",
                "failed",
                "busy",
                "no answer",
                "cancelled",
                "canceled",
            }
        ):
            event_status = "answered"
        elif not event_status and active in {"0", "false", "no", "inactive"}:
            event_status = "completed"
        if not event_status:
            return Response(
                {"detail": "A call status or isActive value is required."},
                status=400,
            )

        try:
            notification = update_voice_call_from_callback(
                session_id,
                event_status,
            )
        except ValueError as error:
            return Response({"detail": str(error)}, status=400)
        if notification is None:
            return Response(
                {"detail": "No voice call matches this provider session."},
                status=404,
            )

        if (
            notification.status == EmergencyNotification.Status.ANSWERED
            and (
                normalized_status in {
                    "answered",
                    "active",
                    "in progress",
                }
                or active in {"1", "true", "yes", "active"}
            )
        ):
            announcement = escape(
                generate_emergency_voice_announcement(
                    notification.incident,
                    notification.recipient,
                )
            )
            return HttpResponse(
                (
                    '<?xml version="1.0" encoding="UTF-8"?>'
                    f"<Response><Say>{announcement}</Say><Hangup/></Response>"
                ),
                content_type="application/xml",
            )

        return HttpResponse("OK", content_type="text/plain")
