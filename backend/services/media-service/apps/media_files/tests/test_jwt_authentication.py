from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from apps.media_files.infrastructure.jwt_authentication import JWTAuthentication


def _generate_keypair() -> tuple[str, str]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")
    return private_pem, public_pem


PRIVATE_KEY, PUBLIC_KEY = _generate_keypair()


class FakeJWKSClient:
    def get_public_key(self, kid=None, header=None):
        return PUBLIC_KEY


class DummyHeaders(dict):
    def get(self, key, default=None):
        return super().get(key, default)


class DummyRequest:
    def __init__(self, token: str):
        self.META = {"HTTP_AUTHORIZATION": f"Bearer {token}"}
        self.headers = DummyHeaders()


def build_token() -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": "user-123",
            "phone_number": "09123456789",
            "role": "USER",
            "type": "access",
            "jti": "jti-123",
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=15)).timestamp()),
            "iss": "hamdong.identity-service",
            "aud": "hamdong.services",
        },
        PRIVATE_KEY,
        algorithm="RS256",
        headers={"kid": "hamdong-main-key", "typ": "JWT"},
    )


def test_valid_access_token_is_accepted():
    auth = JWTAuthentication()
    auth.jwks_client = FakeJWKSClient()
    user, token = auth.authenticate(DummyRequest(build_token()))
    assert user.sub == "user-123"
    assert user.phone_number == "09123456789"
    assert user.role == "USER"
    assert user.token_jti == "jti-123"
    assert token
