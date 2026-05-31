import os
from types import SimpleNamespace

import jwt
from django.conf import settings
from rest_framework import exceptions
from rest_framework.authentication import BaseAuthentication

from apps.media_files.infrastructure.jwks_client import get_default_jwks_client, get_jwks


class ServiceUser(SimpleNamespace):
    @property
    def is_authenticated(self):
        return True


class JWKSAuthentication(BaseAuthentication):
    def __init__(self):
        self.jwks_client = get_default_jwks_client()
        self.issuer = os.getenv("JWT_ISSUER") or getattr(settings, "JWT_ISSUER", None)
        self.audience = os.getenv("JWT_AUDIENCE") or getattr(settings, "JWT_AUDIENCE", None)
        self.algorithms = [os.getenv("JWT_ALGORITHM") or getattr(settings, "JWT_ALGORITHM", "RS256")]

    def authenticate_header(self, request):
        return 'Bearer realm="api"'

    def authenticate(self, request):
        header = request.META.get("HTTP_AUTHORIZATION") or request.headers.get("Authorization")
        if not header:
            return None
        if not header.startswith("Bearer "):
            return None
        token = header.split(" ", 1)[1].strip()
        try:
            unverified_header = jwt.get_unverified_header(token)
        except jwt.DecodeError:
            raise exceptions.AuthenticationFailed("Invalid token header")

        try:
            key = self.jwks_client.get_public_key(kid=unverified_header.get("kid"), header=unverified_header)
        except Exception as exc:
            raise exceptions.AuthenticationFailed("Unable to obtain public key for token") from exc

        try:
            payload = jwt.decode(
                token,
                key=key,
                algorithms=self.algorithms,
                issuer=self.issuer,
                audience=self.audience,
            )
        except jwt.ExpiredSignatureError:
            raise exceptions.AuthenticationFailed("Token expired")
        except jwt.InvalidTokenError as exc:
            raise exceptions.AuthenticationFailed(f"Invalid token: {str(exc)}")

        token_type = payload.get("type") or payload.get("typ")
        if token_type != "access":
            raise exceptions.AuthenticationFailed("Invalid token type")

        sub = payload.get("sub")
        if not sub:
            raise exceptions.AuthenticationFailed("Token missing subject")

        phone = payload.get("phone_number") or payload.get("phone")
        role = payload.get("role")
        display_name = payload.get("display_name")
        is_active = payload.get("is_active", True)
        jti = payload.get("jti")
        user = ServiceUser(
            id=sub,
            sub=sub,
            identity_user_id=sub,
            phone_number=phone,
            display_name=display_name,
            role=role,
            is_active=is_active,
            jti=jti,
            payload=payload,
        )
        user.username = phone or str(sub)
        return user, token


class JWTAuthentication(JWKSAuthentication):
    pass
