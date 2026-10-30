from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import AuthorityVerificationDocument
from .serializers import AuthorityVerificationDocumentSerializer


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