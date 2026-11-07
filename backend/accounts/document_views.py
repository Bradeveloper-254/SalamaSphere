from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import AuthorityVerificationDocument
from .serializers import AuthorityVerificationDocumentSerializer
from notifications.services import (
    create_system_notification,
    get_administrators,
)


class AuthorityVerificationDocumentUploadView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = AuthorityVerificationDocumentSerializer(
            data=request.data,
            context={"request": request},
        )

        serializer.is_valid(raise_exception=True)

        document = serializer.save(
            authority=request.user,
        )
        for administrator in get_administrators():
            create_system_notification(
                recipient=administrator,
                title="Authority verification document submitted",
                message=(
                    f"{request.user.get_username()} submitted a "
                    f"{document.get_document_type_display()} for review."
                ),
            )

        return Response(
            {
                "message": "Verification document submitted successfully.",
                "document": AuthorityVerificationDocumentSerializer(
                    document,
                    context={"request": request},
                ).data,
            },
            status=status.HTTP_201_CREATED,
        )