import os
from types import SimpleNamespace

import jwt
from rest_framework import exceptions
from rest_framework.authentication import BaseAuthentication

from .jwks_client import get_default_jwks_client


class ServiceUser(SimpleNamespace):
    @property
    def is_authenticated(self):
        return True


class JWKSAuthentication(BaseAuthentication):
    """DRF authentication that validates RS256 JWTs using a local PEM or JWKS.

    Behavior:
    - Reads `Authorization: Bearer <token>` header
    - Uses `IDENTITY_PUBLIC_KEY_PATH` (PEM) if present, otherwise fetches JWKS
    - Validates issuer, audience, expiration, and token `type` == 'access'
    - Extracts `sub`, `phone_number`, `role`, `jti` and returns a lightweight user object
    """

    def __init__(self):
        self.jwks_client = get_default_jwks_client()
        self.issuer = os.getenv("JWT_ISSUER")
        self.audience = os.getenv("JWT_AUDIENCE")
        self.algorithms = [os.getenv("JWT_ALGORITHM", "RS256")]

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

        kid = unverified_header.get("kid")
        # fetch key (PEM or RSA key)
        try:
            key = self.jwks_client.get_public_key(kid=kid, header=unverified_header)
        except Exception as exc:
            raise exceptions.AuthenticationFailed("Unable to obtain public key for token") from exc

        # Validate token
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

        # Validate token type (some systems put it in payload as `type`)
        token_type = payload.get("type") or payload.get("typ")
        if token_type != "access":
            raise exceptions.AuthenticationFailed("Invalid token type")

        sub = payload.get("sub")
        if not sub:
            raise exceptions.AuthenticationFailed("Token missing subject")

        phone = payload.get("phone_number") or payload.get("phone")
        role = payload.get("role")
        jti = payload.get("jti")

        # include `sub` to match expected attribute access in services
        user = ServiceUser(id=sub, sub=sub, identity_user_id=sub, phone_number=phone, role=role, jti=jti)
        # also provide a convenient `username` attribute
        user.username = phone or str(sub)
        return (user, token)


# alias expected by views/modules
class JWTAuthentication(JWKSAuthentication):
    pass
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.conf import settings
import jwt
from apps.expenses.infrastructure.jwks_client import get_jwks


class JWTPayload:
    def __init__(self, payload: dict):
        self.payload = payload

    @property
    def sub(self):
        return self.payload.get("sub")

    @property
    def phone_number(self):
        return self.payload.get("phone_number")

    @property
    def role(self):
        return self.payload.get("role")


class JWTAuthentication(BaseAuthentication):
    def authenticate_header(self, request):
        return "Bearer"

    def authenticate(self, request):
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise AuthenticationFailed({"code": "NOT_AUTHENTICATED", "message": "Authentication credentials were not provided."})

        token = auth_header[7:]
        jwks = get_jwks()
        public_key = None
        if jwks and "pem" in jwks:
            public_key = jwks["pem"]

        try:
            if public_key:
                payload = jwt.decode(
                    token,
                    public_key,
                    algorithms=[settings.JWT_ALGORITHM],
                    audience=settings.JWT_AUDIENCE,
                    issuer=settings.JWT_ISSUER,
                )
            else:
                payload = jwt.decode(token, options={"verify_signature": False})

            if payload.get("type") != "access":
                raise AuthenticationFailed({"code": "INVALID_TOKEN", "message": "The provided token is invalid."})

            user_obj = JWTPayload(payload)
            request.user = user_obj
            return (user_obj, None)
        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed({"code": "INVALID_TOKEN", "message": "The provided token is invalid."})
        except jwt.InvalidTokenError:
            raise AuthenticationFailed({"code": "INVALID_TOKEN", "message": "The provided token is invalid."})
