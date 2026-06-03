from types import SimpleNamespace

import jwt
from rest_framework import exceptions
from rest_framework.authentication import BaseAuthentication

from apps.expenses.infrastructure.jwks_client import get_default_jwks_client


class ServiceUser(SimpleNamespace):
    @property
    def is_authenticated(self):
        return True


class JWTAuthentication(BaseAuthentication):
    def __init__(self):
        self.jwks_client = get_default_jwks_client()

    def authenticate_header(self, request):
        return "Bearer"

    def authenticate(self, request):
        header = request.META.get("HTTP_AUTHORIZATION") or request.headers.get("Authorization")
        if not header or not header.startswith("Bearer "):
            raise exceptions.AuthenticationFailed(
                {"code": "NOT_AUTHENTICATED", "message": "Authentication credentials were not provided."}
            )

        token = header.split(" ", 1)[1].strip()
        try:
            unverified_header = jwt.get_unverified_header(token)
        except jwt.DecodeError as exc:
            raise exceptions.AuthenticationFailed(
                {"code": "INVALID_TOKEN", "message": "The provided token is invalid."}
            ) from exc

        try:
            key = self.jwks_client.get_public_key(kid=unverified_header.get("kid"), header=unverified_header)
            payload = jwt.decode(
                token,
                key=key,
                algorithms=["RS256", "HS256"],
                options={
                    "verify_aud": False,
                    "verify_iss": False,
                },
            )
        except jwt.ExpiredSignatureError as exc:
            raise exceptions.AuthenticationFailed(
                {"code": "INVALID_TOKEN", "message": "The provided token is invalid."}
            ) from exc
        except jwt.InvalidTokenError as exc:
            raise exceptions.AuthenticationFailed(
                {"code": "INVALID_TOKEN", "message": "The provided token is invalid."}
            ) from exc
        except Exception as exc:
            raise exceptions.AuthenticationFailed(
                {"code": "INVALID_TOKEN", "message": "The provided token is invalid."}
            ) from exc

        if (payload.get("type") or payload.get("typ")) != "access":
            raise exceptions.AuthenticationFailed(
                {"code": "INVALID_TOKEN", "message": "The provided token is invalid."}
            )

        user_id = payload.get("sub")
        if not user_id:
            raise exceptions.AuthenticationFailed(
                {"code": "INVALID_TOKEN", "message": "The provided token is invalid."}
            )

        user = ServiceUser(
            id=user_id,
            sub=user_id,
            identity_user_id=user_id,
            phone_number=payload.get("phone_number") or payload.get("phone"),
            role=payload.get("role"),
            jti=payload.get("jti"),
        )
        return (user, token)
