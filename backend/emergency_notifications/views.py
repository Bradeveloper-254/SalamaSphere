import hmac
import logging
from xml.sax.saxutils import escape

from django.conf import settings
from django.http import HttpResponse
from rest_framework.parsers import FormParser, JSONParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .voice_services import update_voice_call_from_callback

logger = logging.getLogger(__name__)
MAX_CALLBACK_BYTES = 16 * 1024


class AfricasTalkingCallbackBase(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    parser_classes = [FormParser, JSONParser]

    def callback_error(self, request):
        try:
            content_length = int(request.META.get("CONTENT_LENGTH") or 0)
        except (TypeError, ValueError):
            return Response({"detail": "Malformed callback length."}, status=400)
        if content_length > MAX_CALLBACK_BYTES or len(request.body) > MAX_CALLBACK_BYTES:
            return Response({"detail": "Callback payload is too large."}, status=413)
        expected = settings.AT_VOICE_CALLBACK_TOKEN
        supplied = request.query_params.get("token", "")
        if not expected:
            return Response({"detail": "Voice callbacks are not configured."}, status=503)
        if not hmac.compare_digest(supplied.encode("utf-8"), expected.encode("utf-8")):
            logger.warning("Africa's Talking callback rejected: invalid token")
            return Response({"detail": "Invalid callback token."}, status=403)
        return None


class AfricasTalkingVoiceControlView(AfricasTalkingCallbackBase):
    """Stateless VoiceXML control endpoint; safe before session persistence."""

    def post(self, request):
        error = self.callback_error(request)
        if error:
            return error
        payload = request.data
        session_id = str(payload.get("sessionId") or "")[:150]
        active = str(payload.get("isActive", "")).strip().lower()
        logger.info(
            "Africa's Talking call-control callback received session_id=%s active=%s",
            session_id or "unavailable",
            active or "unavailable",
        )
        # AT calls this endpoint when a call becomes active and expects
        # VoiceXML. No database lookup is safe here: callbacks may race the
        # API response that persists sessionId.
        if active in {"1", "true", "yes", "active"}:
            announcement = (
                "Hello. This is a test automated voice call from "
                "SalamaSphere. The SalamaSphere team is testing the "
                "automated emergency notification system. No emergency "
                "has been triggered. This is not a real emergency. "
                "Thank you for your time."
                if settings.AT_VOICE_TEST_ANNOUNCEMENT
                else "This is an automated SalamaSphere emergency alert. "
                "A person who listed you as a trusted contact needs help. "
                "Please contact them as soon as possible."
            )
            announcement = escape(announcement)
            return HttpResponse(
                '<?xml version="1.0" encoding="UTF-8"?>'
                f"<Response><Say>{announcement}</Say><Hangup/></Response>",
                content_type="application/xml; charset=utf-8",
            )
        return HttpResponse("OK", content_type="text/plain; charset=utf-8")


class AfricasTalkingVoiceEventsView(AfricasTalkingCallbackBase):
    """Status events endpoint; events are acknowledged even when unmatched."""

    def post(self, request):
        error = self.callback_error(request)
        if error:
            return error
        payload = request.data
        session_id = str(payload.get("sessionId") or "").strip()
        client_request_id = str(payload.get("clientRequestId") or "").strip()
        event_status = str(payload.get("status") or "").strip()
        if (
            len(session_id) > 150
            or len(client_request_id) > 150
            or len(event_status) > 50
            or not event_status
            or not (session_id or client_request_id)
        ):
            return Response({"detail": "Malformed voice event."}, status=400)
        try:
            notification = update_voice_call_from_callback(
                session_id,
                event_status,
                client_request_id=client_request_id,
            )
        except ValueError:
            logger.warning("Africa's Talking voice event has unknown status")
            return Response({"detail": "Unsupported call status."}, status=400)
        logger.info(
            "Africa's Talking call event correlated=%s notification_id=%s session_id=%s status=%s",
            bool(notification),
            str(notification.pk) if notification else "unmatched",
            session_id or "unavailable",
            event_status.lower()[:50],
        )
        # Acknowledge unmatched events so provider retries do not create noise.
        return HttpResponse("OK", content_type="text/plain; charset=utf-8")
