from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from rest_framework import exceptions
from rest_framework.test import APIRequestFactory

from apps.groups.infrastructure.auth_errors import JWTPublicKeyUnavailable
from apps.groups.infrastructure.exception_handlers import api_exception_handler
from apps.groups.infrastructure.jwks_client import JWKSClientError
from apps.groups.infrastructure.jwt_authentication import JWTAuthentication


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
    def __init__(self, public_key: str):
        self.public_key = public_key

    def get_public_key(self, kid=None, header=None):
        return self.public_key


class UnavailableJWKSClient:
    def get_public_key(self, kid=None, header=None):
        raise JWKSClientError("JWT public key is not available.")


def build_token(*, private_key: str = PRIVATE_KEY, **overrides) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": "user-123",
        "email": "09123456789",
        "role": "USER",
        "type": "access",
        "jti": "jti-123",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=15)).timestamp()),
        "iss": "hamdong.identity-service",
        "aud": "hamdong.services",
    }
    payload.update(overrides)
    return jwt.encode(
        payload,
        private_key,
        algorithm="RS256",
        headers={"kid": "hamdong-main-key", "typ": "JWT"},
    )


def make_request(token: str | None = None):
    factory = APIRequestFactory()
    if token is None:
        return factory.get("/api/v1/groups/")
    return factory.get("/api/v1/groups/", HTTP_AUTHORIZATION=f"Bearer {token}")


def make_auth(public_key: str = PUBLIC_KEY):
    auth = JWTAuthentication()
    auth.jwks_client = FakeJWKSClient(public_key)
    return auth


def test_valid_access_token_is_accepted():
    user, token = make_auth().authenticate(make_request(build_token()))
    assert user.sub == "user-123"
    assert user.email == "09123456789"
    assert user.role == "USER"
    assert user.token_jti == "jti-123"
    assert token


def test_missing_token_returns_not_authenticated():
    with pytest.raises(exceptions.NotAuthenticated) as exc_info:
        make_auth().authenticate(make_request())

    response = api_exception_handler(exc_info.value, {})
    assert response.status_code == 401
    assert response.data == {
        "error": {
            "code": "NOT_AUTHENTICATED",
            "message": "Authentication credentials were not provided.",
        }
    }


def test_invalid_signature_returns_invalid_token():
    other_private_key, _ = _generate_keypair()
    with pytest.raises(exceptions.AuthenticationFailed) as exc_info:
        make_auth().authenticate(make_request(build_token(private_key=other_private_key)))

    response = api_exception_handler(exc_info.value, {})
    assert response.status_code == 401
    assert response.data["error"]["code"] == "INVALID_TOKEN"


def test_expired_token_returns_token_expired():
    expired = build_token(exp=int((datetime.now(timezone.utc) - timedelta(minutes=1)).timestamp()))
    with pytest.raises(exceptions.AuthenticationFailed) as exc_info:
        make_auth().authenticate(make_request(expired))

    response = api_exception_handler(exc_info.value, {})
    assert response.status_code == 401
    assert response.data["error"]["code"] == "TOKEN_EXPIRED"


def test_refresh_token_used_as_access_returns_invalid_token_type():
    token = build_token(type="refresh")
    with pytest.raises(exceptions.AuthenticationFailed) as exc_info:
        make_auth().authenticate(make_request(token))

    response = api_exception_handler(exc_info.value, {})
    assert response.status_code == 401
    assert response.data["error"]["code"] == "INVALID_TOKEN_TYPE"


def test_wrong_audience_returns_invalid_token():
    token = build_token(aud="wrong-audience")
    with pytest.raises(exceptions.AuthenticationFailed) as exc_info:
        make_auth().authenticate(make_request(token))

    response = api_exception_handler(exc_info.value, {})
    assert response.status_code == 401
    assert response.data["error"]["code"] == "INVALID_TOKEN"


def test_wrong_issuer_returns_invalid_token():
    token = build_token(iss="wrong-issuer")
    with pytest.raises(exceptions.AuthenticationFailed) as exc_info:
        make_auth().authenticate(make_request(token))

    response = api_exception_handler(exc_info.value, {})
    assert response.status_code == 401
    assert response.data["error"]["code"] == "INVALID_TOKEN"


def test_missing_public_key_returns_service_unavailable():
    auth = JWTAuthentication()
    auth.jwks_client = UnavailableJWKSClient()

    with pytest.raises(JWTPublicKeyUnavailable) as exc_info:
        auth.authenticate(make_request(build_token()))

    response = api_exception_handler(exc_info.value, {})
    assert response.status_code == 503
    assert response.data == {
        "error": {
            "code": "JWT_PUBLIC_KEY_UNAVAILABLE",
            "message": "JWT public key is not available.",
        }
    }


def test_no_unsafe_jwt_decode_in_production_code():
    services_root = Path(__file__).resolve().parents[4]
    disallowed = (
        '"verify_signature": False',
        "\"verify_signature': False",
        "verify=False",
        '"verify_exp": False',
        "\"verify_exp': False",
    )
    production_files = [
        path
        for path in services_root.rglob("*.py")
        if "tests" not in path.parts and path.name != "README.md"
    ]
    for file_path in production_files:
        contents = file_path.read_text(encoding="utf-8")
        assert not any(pattern in contents for pattern in disallowed), file_path
