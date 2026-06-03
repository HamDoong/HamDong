"""JWT authentication backend for identity service."""

from __future__ import annotations

from rest_framework import exceptions
from rest_framework.authentication import BaseAuthentication

from apps.identity.application.token_service import TokenService
from apps.identity.infrastructure.auth_user import AuthenticatedUser
from apps.identity.infrastructure.repositories import UserRepository


class JWTAuthentication(BaseAuthentication):
    """Authenticate requests using signed Bearer JWT access tokens."""

    def authenticate_header(self, request):
        return "Bearer"

    def authenticate(self, request):
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if not auth_header:
            raise exceptions.NotAuthenticated(
                {"code": "NOT_AUTHENTICATED", "message": "Authentication credentials were not provided."}
            )

        parts = auth_header.split(" ", 1)
        if len(parts) != 2 or parts[0] != "Bearer" or not parts[1].strip():
            raise exceptions.NotAuthenticated(
                {"code": "NOT_AUTHENTICATED", "message": "Authentication credentials were not provided."}
            )

        token = parts[1].strip()
        token_service = TokenService()
        payload = token_service.verify_access_token(token)

        if not payload:
            raise exceptions.AuthenticationFailed(
                {"code": "INVALID_TOKEN", "message": "The provided token is invalid."}
            )

        if not UserRepository.get_by_id(payload.get("sub")):
            raise exceptions.AuthenticationFailed(
                {"code": "INVALID_TOKEN", "message": "The provided token is invalid."}
            )

        user = AuthenticatedUser(
            id=str(payload["sub"]),
            phone_number=payload.get("phone_number"),
            role=str(payload["role"]),
            token_jti=str(payload["jti"]),
        )
        request.user = user
        return user, token
