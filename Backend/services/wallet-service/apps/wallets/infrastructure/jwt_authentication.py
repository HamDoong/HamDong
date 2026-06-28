from __future__ import annotations

import os

import jwt
from django.conf import settings
from rest_framework import exceptions
from rest_framework.authentication import BaseAuthentication

from apps.wallets.infrastructure.auth_errors import JWTPublicKeyUnavailable
from apps.wallets.infrastructure.auth_user import AuthenticatedUser
from apps.wallets.infrastructure.jwks_client import JWKSClientError, get_default_jwks_client


_REQUIRED_ACCESS_CLAIMS = (
    "sub",
    "email",
    "role",
    "type",
    "jti",
    "iat",
    "exp",
    "iss",
    "aud",
)


class JWTAuthentication(BaseAuthentication):
    def __init__(self) -> None:
        self.jwks_client = get_default_jwks_client()
        self.algorithm = os.getenv("JWT_ALGORITHM") or getattr(settings, "JWT_ALGORITHM", "RS256")
        self.issuer = os.getenv("JWT_ISSUER") or getattr(settings, "JWT_ISSUER", "hamdong.identity-service")
        self.audience = os.getenv("JWT_AUDIENCE") or getattr(settings, "JWT_AUDIENCE", "hamdong.services")

    def authenticate_header(self, request) -> str:
        return "Bearer"

    def authenticate(self, request):
        token = self._get_token(request)
        header = self._get_unverified_header(token)
        public_key = self._get_public_key(header)
        try:
            payload = jwt.decode(
                token,
                key=public_key,
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

        user = AuthenticatedUser(
            id=str(payload["sub"]),
            email=payload.get("email"),
            role=str(payload["role"]),
            token_jti=str(payload["jti"]),
        )
        return user, token

    def _get_token(self, request) -> str:
        header = request.META.get("HTTP_AUTHORIZATION", "")
        if not header:
            raise exceptions.NotAuthenticated(
                {"code": "NOT_AUTHENTICATED", "message": "Authentication credentials were not provided."}
            )
        prefix, _, token = header.partition(" ")
        if prefix.lower() != "bearer" or not token:
            raise exceptions.AuthenticationFailed(
                {"code": "INVALID_TOKEN", "message": "The provided token is invalid."}
            )
        return token.strip()

    def _get_unverified_header(self, token: str) -> dict:
        try:
            return jwt.get_unverified_header(token)
        except jwt.InvalidTokenError as exc:
            raise exceptions.AuthenticationFailed(
                {"code": "INVALID_TOKEN", "message": "The provided token is invalid."}
            ) from exc

    def _get_public_key(self, header: dict):
        try:
            return self.jwks_client.get_public_key(header.get("kid"), header)
        except JWKSClientError as exc:
            raise JWTPublicKeyUnavailable() from exc
