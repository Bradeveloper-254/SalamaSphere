import json
import logging
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings


logger = logging.getLogger(__name__)


class TranscriptionError(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


class OpenAITranscriptionProvider:
    endpoint = "https://api.openai.com/v1/audio/transcriptions"

    def transcribe(self, audio_bytes, filename, mime_type, language=None):
        token = settings.OPENAI_API_KEY
        if not token:
            raise TranscriptionError("provider_not_configured")

        boundary = "SalamaSphereTranscriptionBoundary"
        parts = []
        def field(name, value):
            parts.extend([
                f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n".encode(),
                str(value).encode(), b"\r\n",
            ])
        field("model", settings.SPEECH_TO_TEXT_MODEL)
        field("response_format", "json")
        field("timestamp_granularities[]", "segment")
        if language:
            field("language", language)
        parts.extend([
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"audio\"\r\nContent-Type: {mime_type}\r\n\r\n".encode(),
            audio_bytes,
            b"\r\n",
            f"--{boundary}--\r\n".encode(),
        ])
        request = Request(
            self.endpoint,
            data=b"".join(parts),
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": f"multipart/form-data; boundary={boundary}",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=90) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            logger.warning("Speech provider returned HTTP %s", exc.code)
            raise TranscriptionError("provider_request_failed") from exc
        except (URLError, TimeoutError, OSError, ValueError) as exc:
            logger.warning("Speech provider request failed (%s)", type(exc).__name__)
            raise TranscriptionError("provider_unavailable") from exc

        transcript = payload.get("text")
        if not isinstance(transcript, str) or not transcript.strip():
            raise TranscriptionError("no_speech_recognized")
        detected = payload.get("language")
        if not detected:
            detected = "sw" if language == "sw" else "en" if language == "en" else "und"
        return transcript.strip(), detected
