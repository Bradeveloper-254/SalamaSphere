from rest_framework.permissions import BasePermission


class IsSalamaSphereAdmin(BasePermission):
    """
    Allow only authenticated, active SalamaSphere administrators.
    """

    def has_permission(self, request, view):
        user = request.user

        return bool(
            user
            and user.is_authenticated
            and user.is_active
            and (
                user.is_superuser
                or (
                    user.is_staff
                    and user.role == "admin"
                )
            )
        )
        
class IsApprovedAuthority(BasePermission):
    """
    Permit access only to active, approved authority accounts.
    """

    def has_permission(self, request, view):
        user = request.user

        return bool(
            user
            and user.is_authenticated
            and user.is_active
            and user.role == "authority"
            and user.authority_status == "approved"
        )