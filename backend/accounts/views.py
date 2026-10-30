from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from rest_framework.throttling import AnonRateThrottle

from .serializers import RegistrationSerializer


class RegistrationView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [AnonRateThrottle]

    def post(self, request):
        serializer = RegistrationSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = serializer.save()

        return Response(
            {
                "message": (
                    "Registration successful. "
                    "Your authority account is awaiting approval."
                    if user.role == user.Role.AUTHORITY
                    else "Survivor registration successful."
                ),
                "username": user.username,
                "role": user.role,
                "authority_status": user.authority_status,
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")

        if not username or not password:
            return Response(
                {"detail": "Username and password are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = authenticate(
            request=request,
            username=username,
            password=password,
        )

        if user is None:
            return Response(
                {"detail": "Invalid username or password."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not user.is_active:
            return Response(
                {"detail": "This account is inactive."},
                status=status.HTTP_403_FORBIDDEN,
            )

        token, _ = Token.objects.get_or_create(user=user)

        return Response(
            {
                "token": token.key,
                "username": user.get_username(),
                "role": user.role,
                "is_superuser": user.is_superuser,
                "authority_status": user.authority_status,
            },
            status=status.HTTP_200_OK,
        )



logger = logging.getLogger(__name__)


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [AnonRateThrottle]

    def post(self, request):
        email = request.data.get("email", "")

        if not isinstance(email, str) or not email.strip():
            return Response(
                {"detail": "Please provide an email address."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        User = get_user_model()
        users = User.objects.filter(
            email__iexact=email.strip(),
            is_active=True,
        )

        # Always return the same public message so the endpoint
        # does not reveal whether an email has an account.
        for user in users:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)

            subject = "SalamaSphere password reset"
            message = (
                f"Hello {user.get_username()},\n\n"
                "A password reset was requested for your "
                "SalamaSphere account.\n\n"
                f"Reset user ID: {uid}\n"
                f"Reset token: {token}\n\n"
                "Open SalamaSphere, choose Forgot Password, "
                "and enter the user ID and token above on the "
                "password reset confirmation page.\n\n"
                "If you did not request this, you can ignore "
                "this email. Never share your reset token.\n"
            )

            try:
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=False,
                )
            except Exception:
                logger.exception(
                    "Could not send a password-reset email."
                )

        return Response(
            {
                "message": (
                    "If an active account matches that email, "
                    "password-reset instructions will be sent."
                )
            },
            status=status.HTTP_200_OK,
        )


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [AnonRateThrottle]

    def post(self, request):
        uid = request.data.get("uid", "")
        token = request.data.get("token", "")
        new_password = request.data.get("new_password", "")

        if not all(
            isinstance(value, str) and value
            for value in (uid, token, new_password)
        ):
            return Response(
                {
                    "detail": (
                        "User ID, reset token, and new password "
                        "are required."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user_id = force_str(urlsafe_base64_decode(uid))
            user = get_user_model().objects.get(
                pk=user_id,
                is_active=True,
            )
        except (
            ValueError,
            TypeError,
            OverflowError,
            UnicodeDecodeError,
            get_user_model().DoesNotExist,
        ):
            return Response(
                {"detail": "The reset link is invalid or expired."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not default_token_generator.check_token(user, token):
            return Response(
                {"detail": "The reset link is invalid or expired."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            validate_password(new_password, user=user)
        except ValidationError as error:
            return Response(
                {"new_password": list(error.messages)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(new_password)
        user.save(update_fields=["password"])

        # Invalidate existing DRF authentication tokens after
        # the password is changed.
        from rest_framework.authtoken.models import Token
        Token.objects.filter(user=user).delete()

        return Response(
            {
                "message": (
                    "Password reset successful. Please log in "
                    "with your new password."
                )
            },
            status=status.HTTP_200_OK,
        )
