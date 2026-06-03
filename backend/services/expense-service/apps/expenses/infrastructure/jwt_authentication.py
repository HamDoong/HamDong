"""JWT authentication for expense-service."""

from __future__ import annotations

import os
from types import SimpleNamespace

import jwt
from rest_framework import exceptions
from rest_framework.authentication import BaseAuthentication

from apps.expenses.infrastructure.jwks_client import get_default_jwks_client


class ServiceUser(SimpleNamespace):
    @property
    def is_authenticated(self) -> bool:
        return True


class JWTAuthentication(BaseAuthentication):
    """Validate bearer access tokens from identity-service."""

    def __init__(self) -> None:
        self.jwks_client = get_default_jwks_client()
        self.issuer = os.getenv("JWT_ISSUER")
        self.audience = os.getenv("JWT_AUDIENCE")
        self.algorithms = [os.getenv("JWT_ALGORITHM", "RS256")]

    def authenticate_header(self, request) -> str:
        return "Bearer"

    def authenticate(self, request):
        header = request.META.get("HTTP_AUTHORIZATION") or request.headers.get("Authorization")
        if not header:
            return None
        if not header.startswith("Bearer "):
            return None

        token = header.split(" ", 1)[1].strip()
        try:
            unverified_header = jwt.get_unverified_header(token)
            key = self.jwks_client.get_public_key(
                kid=unverified_header.get("kid"),
                header=unverified_header,
            )
            payload = jwt.decode(
                token,
                key=key,
                algorithms=self.algorithms,
                issuer=self.issuer,
                audience=self.audience,
            )
        except jwt.ExpiredSignatureError as exc:
            raise exceptions.AuthenticationFailed("Token expired") from exc
        except jwt.InvalidTokenError as exc:
            raise exceptions.AuthenticationFailed("Invalid token") from exc
        except Exception as exc:
            raise exceptions.AuthenticationFailed("Unable to validate token") from exc

        if (payload.get("type") or payload.get("typ")) != "access":
            raise exceptions.AuthenticationFailed("Invalid token type")

        subject = payload.get("sub")
        if not subject:
            raise exceptions.AuthenticationFailed("Token missing subject")

        user = ServiceUser(
            id=subject,
            sub=subject,
            identity_user_id=subject,
            phone_number=payload.get("phone_number") or payload.get("phone"),
            role=payload.get("role"),
            jti=payload.get("jti"),
        )
        user.username = user.phone_number or str(subject)
        return user, token


JWKSAuthentication = JWTAuthentication
