from django.contrib.auth import get_user_model
from django.db import transaction

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import AuthorityApprovalLog, AuthorityAccountStatusLog
from .models import AuthorityApprovalLog
from .permissions import IsSalamaSphereAdmin

User = get_user_model()


class PendingAuthorityApplicationsView(APIView):
    permission_classes = [
        IsAuthenticated,
        IsSalamaSphereAdmin,
    ]

    def get(self, request):
        applications = User.objects.filter(
            role=User.Role.AUTHORITY,
            authority_status=User.AuthorityStatus.PENDING,
        ).order_by("date_joined")

        results = [
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "phone_number": user.phone_number,
                "authority_status": user.authority_status,
                "date_joined": user.date_joined,
            }
            for user in applications
        ]

        from rest_framework.serializers import DateTimeField

        date_field = DateTimeField()

        for item in results:
            item["date_joined"] = date_field.to_representation(
                item["date_joined"]
            )

        return Response(results)


class AuthorityDecisionView(APIView):
    permission_classes = [
        IsAuthenticated,
        IsSalamaSphereAdmin,
    ]

    decision = None

    @transaction.atomic
    def post(self, request, user_id):
        try:
            authority = User.objects.select_for_update().get(
                pk=user_id,
                role=User.Role.AUTHORITY,
            )
        except User.DoesNotExist:
            return Response(
                {"detail": "Authority application not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if authority.authority_status != User.AuthorityStatus.PENDING:
            return Response(
                {
                    "detail": (
                        "This application is no longer pending. "
                        "Review the existing decision before proceeding."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        if authority.pk == request.user.pk:
            return Response(
                {"detail": "You cannot review your own application."},
                status=status.HTTP_403_FORBIDDEN,
            )

        reason = request.data.get("reason", "")
        if not isinstance(reason, str):
            return Response(
                {"reason": ["Must be a string."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        reason = reason.strip()

        if self.decision == AuthorityApprovalLog.Decision.REJECTED and not reason:
            return Response(
                {"reason": ["A reason is required when rejecting an application."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if len(reason) > 2000:
            return Response(
                {"reason": ["Must be 2000 characters or fewer."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        authority.authority_status = self.decision
        authority.save(update_fields=["authority_status"])

        AuthorityApprovalLog.objects.create(
            authority=authority,
            reviewed_by=request.user,
            decision=self.decision,
            reason=reason,
        )

        return Response(
            {
                "message": (
                    "Authority application approved."
                    if self.decision == AuthorityApprovalLog.Decision.APPROVED
                    else "Authority application rejected."
                ),
                "authority_id": authority.id,
                "authority_status": authority.authority_status,
            },
            status=status.HTTP_200_OK,
        )


class ApproveAuthorityView(AuthorityDecisionView):
    decision = AuthorityApprovalLog.Decision.APPROVED


class RejectAuthorityView(AuthorityDecisionView):
    decision = AuthorityApprovalLog.Decision.REJECTED
    
    
class AuthorityAccountManagementView(APIView):
    permission_classes = [
        IsAuthenticated,
        IsSalamaSphereAdmin,
    ]

    def get(self, request):
        authorities = User.objects.filter(
            role=User.Role.AUTHORITY,
        ).order_by("-date_joined")

        results = [
            {
                "id": authority.id,
                "username": authority.username,
                "email": authority.email,
                "phone_number": authority.phone_number,
                "authority_status": authority.authority_status,
                "is_active": authority.is_active,
                "date_joined": authority.date_joined.isoformat(),
            }
            for authority in authorities
        ]

        return Response(results)


class AuthorityAccountStatusView(APIView):
    permission_classes = [
        IsAuthenticated,
        IsSalamaSphereAdmin,
    ]

    @transaction.atomic
    def post(self, request, user_id):
        action = request.data.get("action")
        reason = request.data.get("reason", "")

        if action not in ("suspend", "reactivate"):
            return Response(
                {"action": ["Choose suspend or reactivate."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not isinstance(reason, str):
            return Response(
                {"reason": ["Must be a string."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        reason = reason.strip()

        if len(reason) > 2000:
            return Response(
                {"reason": ["Must be 2000 characters or fewer."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            authority = User.objects.select_for_update().get(
                pk=user_id,
                role=User.Role.AUTHORITY,
            )
        except User.DoesNotExist:
            return Response(
                {"detail": "Authority account not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Only verified, approved authorities can be suspended/reactivated.
        if authority.authority_status != User.AuthorityStatus.APPROVED:
            return Response(
                {
                    "detail": (
                        "Only approved authority accounts can be "
                        "suspended or reactivated."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        if action == "suspend":
            if not authority.is_active:
                return Response(
                    {"detail": "This authority account is already suspended."},
                    status=status.HTTP_409_CONFLICT,
                )

            authority.is_active = False
            log_action = AuthorityAccountStatusLog.Action.SUSPENDED
            message = "Authority account suspended successfully."

        else:
            if authority.is_active:
                return Response(
                    {"detail": "This authority account is already active."},
                    status=status.HTTP_409_CONFLICT,
                )

            authority.is_active = True
            log_action = AuthorityAccountStatusLog.Action.REACTIVATED
            message = "Authority account reactivated successfully."

        authority.save(update_fields=["is_active"])

        AuthorityAccountStatusLog.objects.create(
            authority=authority,
            changed_by=request.user,
            action=log_action,
            reason=reason,
        )

        return Response(
            {
                "message": message,
                "authority_id": authority.id,
                "authority_status": authority.authority_status,
                "is_active": authority.is_active,
            },
            status=status.HTTP_200_OK,
        )