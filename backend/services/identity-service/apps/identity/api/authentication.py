"""JWT authentication backend for identity service."""

from __future__ import annotations

from django.conf import settings
import jwt
from rest_framework import exceptions
from rest_framework.authentication import BaseAuthentication

from apps.identity.infrastructure.auth_errors import JWTPublicKeyUnavailable
from apps.identity.infrastructure.auth_user import AuthenticatedUser
from apps.identity.infrastructure.key_loader import JwtKeyLoader
from apps.identity.infrastructure.repositories import UserRepository


_REQUIRED_ACCESS_CLAIMS = (
    "sub",
    "phone_number",
    "role",
    "type",
    "jti",
    "iat",
    "exp",
    "iss",
    "aud",
)


class JWTAuthentication(BaseAuthentication):
    """Authenticate requests using signed Bearer JWT access tokens."""

    def __init__(self) -> None:
        self.algorithm = settings.JWT_ALGORITHM
        self.issuer = settings.JWT_ISSUER
        self.audience = settings.JWT_AUDIENCE

    def authenticate_header(self, request):
        return "Bearer"

    def authenticate(self, request):
        token = self._get_token(request)
        header = self._get_unverified_header(token)
        public_key = self._get_public_key()

        try:
            payload = jwt.decode(
                token,
                public_key,
                algorithms=[self.algorithm],
                issuer=self.issuer,
                audience=self.audience,
                options={"require": list(_REQUIRED_ACCESS_CLAIMS)},
            )
        except jwt.ExpiredSignatureError as exc:
            raise exceptions.AuthenticationFailed(
                {"code": "TOKEN_EXPIRED", "message": "The provided token has expired."}
            ) from exc
        except (jwt.InvalidIssuedAtError, jwt.ImmatureSignatureError, jwt.InvalidTokenError) as exc:
            raise exceptions.AuthenticationFailed(
                {"code": "INVALID_TOKEN", "message": "The provided token is invalid."}
            ) from exc

        if payload.get("type") != "access":
            raise exceptions.AuthenticationFailed(
                {"code": "INVALID_TOKEN_TYPE", "message": "Access token is required."}
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

    def _get_token(self, request) -> str:
        auth_header = request.META.get("HTTP_AUTHORIZATION") or request.headers.get("Authorization")
        if not auth_header:
            raise exceptions.NotAuthenticated(
                {"code": "NOT_AUTHENTICATED", "message": "Authentication credentials were not provided."}
            )

        parts = auth_header.split(" ", 1)
        if len(parts) != 2 or parts[0] != "Bearer" or not parts[1].strip():
            raise exceptions.NotAuthenticated(
                {"code": "NOT_AUTHENTICATED", "message": "Authentication credentials were not provided."}
            )
        return parts[1].strip()

    def _get_unverified_header(self, token: str) -> dict:
        try:
            header = jwt.get_unverified_header(token)
        except jwt.InvalidTokenError as exc:
            raise exceptions.AuthenticationFailed(
                {"code": "INVALID_TOKEN", "message": "The provided token is invalid."}
            ) from exc

        if header.get("alg") != self.algorithm:
            raise exceptions.AuthenticationFailed(
                {"code": "INVALID_TOKEN", "message": "The provided token is invalid."}
            )
        return header

    def _get_public_key(self) -> str:
        try:
            return JwtKeyLoader.get_public_key()
        except FileNotFoundError as exc:
            raise JWTPublicKeyUnavailable() from exc
