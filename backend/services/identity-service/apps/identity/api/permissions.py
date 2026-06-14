"""Custom permissions for identity service."""

from rest_framework.permissions import BasePermission

from apps.identity.application.token_service import TokenService


class IsAuthenticated(BasePermission):
    """Custom authentication permission using JWT access tokens."""

    message = "Authentication credentials were not provided or are invalid."

    def has_permission(self, request, view):
        """Check if request has valid access token."""
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")

        if not auth_header.startswith("Bearer "):
            return False

        token = auth_header[7:]  # Remove "Bearer " prefix

        try:
            token_service = TokenService()
            payload = token_service.verify_access_token(token)

            if not payload:
                return False

            # Store user info in request for later use
            request.user_id = payload.get("sub")
            request.email = payload.get("email")
            request.user_role = payload.get("role")

            return True
        except Exception:
            return False
