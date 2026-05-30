"""JWT authentication backend for identity service."""

from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from apps.identity.application.token_service import TokenService
from apps.identity.infrastructure.repositories import UserRepository


class JWTAuthentication(BaseAuthentication):
    """Authenticate requests using Bearer JWT access tokens."""

    def authenticate_header(self, request):
        return "Bearer"

    def authenticate(self, request):
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if not auth_header:
            raise AuthenticationFailed("Authentication credentials were not provided.")

        if not auth_header.startswith("Bearer "):
            raise AuthenticationFailed(
                "Authentication credentials were not provided or are invalid."
            )

        token = auth_header[7:]
        token_service = TokenService()
        payload = token_service.verify_access_token(token)

        if not payload:
            raise AuthenticationFailed(
                "Authentication credentials were not provided or are invalid."
            )

        user = UserRepository.get_by_id(payload.get("sub"))
        if not user:
            raise AuthenticationFailed(
                "Authentication credentials were not provided or are invalid."
            )

        request.user = user
        return (user, None)
