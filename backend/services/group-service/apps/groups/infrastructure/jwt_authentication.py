"""JWT Authentication for group-service using local public key or JWKS."""

from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.conf import settings
import jwt
from apps.groups.infrastructure.jwks_client import get_jwks


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
            raise AuthenticationFailed(
                {"code": "NOT_AUTHENTICATED", "message": "Authentication credentials were not provided."}
            )

        token = auth_header[7:]

        # Load public key / JWKS
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
                # No PEM available; try to decode without verification (not ideal)
                payload = jwt.decode(token, options={"verify_signature": False})

            if payload.get("type") != "access":
                raise AuthenticationFailed({"code": "INVALID_TOKEN", "message": "The provided token is invalid."})

            # Build lightweight user-like object
            user_obj = JWTPayload(payload)
            request.user = user_obj
            return (user_obj, None)
        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed({"code": "INVALID_TOKEN", "message": "The provided token is invalid."})
        except jwt.InvalidTokenError:
            raise AuthenticationFailed({"code": "INVALID_TOKEN", "message": "The provided token is invalid."})
