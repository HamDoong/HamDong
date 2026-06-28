"""JWT token generation and verification service."""

from __future__ import annotations

import base64
import uuid
from datetime import datetime, timedelta, timezone as tz
from typing import Any, Dict, Optional, Tuple

import jwt
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from django.conf import settings

from apps.identity.domain.models import User
from apps.identity.infrastructure.key_loader import JwtKeyLoader
from apps.identity.infrastructure.repositories import RefreshTokenRepository

ACCESS_TOKEN_KID = "hamdong-main-key"
ACCESS_REQUIRED_CLAIMS = ["sub", "email", "role", "type", "jti", "iat", "exp", "iss", "aud"]
REFRESH_REQUIRED_CLAIMS = ["sub", "type", "jti", "iat", "exp", "iss", "aud"]


class TokenService:
    """Service for JWT token operations."""

    def __init__(self):
        self.algorithm = settings.JWT_ALGORITHM
        self.issuer = settings.JWT_ISSUER
        self.audience = settings.JWT_AUDIENCE
        self.refresh_audience = settings.JWT_ISSUER
        self.access_token_lifetime = settings.JWT_ACCESS_TOKEN_LIFETIME_SECONDS
        self.refresh_token_lifetime = settings.JWT_REFRESH_TOKEN_LIFETIME_SECONDS
        self.remember_me_refresh_token_lifetime = getattr(settings, "JWT_REMEMBER_ME_REFRESH_TOKEN_LIFETIME_SECONDS", self.refresh_token_lifetime)
        self.private_key = JwtKeyLoader.get_private_key()
        self.public_key = JwtKeyLoader.get_public_key()

    def generate_tokens(
        self,
        user: User,
        user_agent: str = None,
        ip_address: str = None,
        *,
        remember_me: bool = False,
        refresh_lifetime_seconds: int | None = None,
    ) -> Tuple[str, str, str]:
        jti = str(uuid.uuid4())
        lifetime_seconds = refresh_lifetime_seconds if refresh_lifetime_seconds is not None else (
            self.remember_me_refresh_token_lifetime if remember_me else self.refresh_token_lifetime
        )
        access_token = self._create_access_token(user, jti)
        refresh_token, refresh_token_hash = self._create_refresh_token(user, jti, lifetime_seconds=lifetime_seconds)
        RefreshTokenRepository.create(
            user=user,
            token_hash=refresh_token_hash,
            jti=jti,
            lifetime_seconds=lifetime_seconds,
            remember_me=remember_me,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        return access_token, refresh_token, jti

    def _encode(self, payload: dict[str, Any]) -> str:
        return jwt.encode(
            payload,
            self.private_key,
            algorithm=self.algorithm,
            headers={"kid": ACCESS_TOKEN_KID, "typ": "JWT"},
        )

    def _create_access_token(self, user: User, jti: str) -> str:
        now = datetime.now(tz.utc)
        expires_at = now + timedelta(seconds=self.access_token_lifetime)
        payload = {
            "sub": str(user.id),
            "email": user.email,
            "role": user.role,
            "type": "access",
            "jti": jti,
            "iat": int(now.timestamp()),
            "exp": int(expires_at.timestamp()),
            "iss": self.issuer,
            "aud": self.audience,
        }
        return self._encode(payload)

    def _create_refresh_token(self, user: User, jti: str, *, lifetime_seconds: int) -> Tuple[str, str]:
        now = datetime.now(tz.utc)
        expires_at = now + timedelta(seconds=lifetime_seconds)
        payload = {
            "sub": str(user.id),
            "type": "refresh",
            "jti": jti,
            "iat": int(now.timestamp()),
            "exp": int(expires_at.timestamp()),
            "iss": self.issuer,
            "aud": self.refresh_audience,
        }
        token = self._encode(payload)
        token_hash = RefreshTokenRepository.hash_token(token)
        return token, token_hash

    def verify_access_token_details(self, token: str) -> tuple[Optional[Dict[str, Any]], Optional[str]]:
        try:
            header = jwt.get_unverified_header(token)
            if header.get("alg") != self.algorithm:
                return None, "INVALID_TOKEN"
            payload = jwt.decode(
                token,
                self.public_key,
                algorithms=[self.algorithm],
                audience=self.audience,
                issuer=self.issuer,
                options={"require": ACCESS_REQUIRED_CLAIMS},
            )
        except jwt.ExpiredSignatureError:
            return None, "TOKEN_EXPIRED"
        except jwt.InvalidTokenError:
            return None, "INVALID_TOKEN"

        if payload.get("type") != "access":
            return None, "INVALID_TOKEN_TYPE"
        return payload, None

    def verify_access_token(self, token: str) -> Optional[Dict[str, Any]]:
        payload, _ = self.verify_access_token_details(token)
        return payload

    def verify_refresh_token(self, token: str) -> Optional[Dict[str, Any]]:
        try:
            header = jwt.get_unverified_header(token)
            if header.get("alg") != self.algorithm:
                return None
            payload = jwt.decode(
                token,
                self.public_key,
                algorithms=[self.algorithm],
                audience=self.refresh_audience,
                issuer=self.issuer,
                options={"require": REFRESH_REQUIRED_CLAIMS},
            )
        except jwt.InvalidTokenError:
            return None

        if payload.get("type") != "refresh":
            return None

        token_hash = RefreshTokenRepository.hash_token(token)
        db_token = RefreshTokenRepository.get_by_token_hash(token_hash)
        if not db_token or db_token.is_revoked or RefreshTokenRepository.is_expired(db_token):
            return None
        return payload

    def refresh_tokens(
        self, refresh_token: str, user_agent: str = None, ip_address: str = None
    ) -> Optional[Tuple[str, str]]:
        payload = self.verify_refresh_token(refresh_token)
        if not payload:
            return None

        user = User.objects.filter(id=payload.get("sub"), deleted_at__isnull=True).first()
        if not user or not user.is_active:
            return None

        token_hash = RefreshTokenRepository.hash_token(refresh_token)
        old_token = RefreshTokenRepository.get_by_token_hash(token_hash)
        if not old_token:
            return None

        remember_me = bool(getattr(old_token, "remember_me", False))
        RefreshTokenRepository.revoke(old_token)
        access_token, new_refresh_token, _ = self.generate_tokens(
            user,
            user_agent=user_agent,
            ip_address=ip_address,
            remember_me=remember_me,
        )
        return access_token, new_refresh_token

    def get_jwks(self) -> Dict[str, Any]:
        public_key_obj = serialization.load_pem_public_key(
            self.public_key.encode(),
            backend=default_backend(),
        )
        public_numbers = public_key_obj.public_numbers()

        def int_to_base64(value: int) -> str:
            bytes_value = value.to_bytes((value.bit_length() + 7) // 8, "big")
            return base64.urlsafe_b64encode(bytes_value).rstrip(b"=").decode("utf-8")

        return {
            "keys": [
                {
                    "kty": "RSA",
                    "use": "sig",
                    "kid": ACCESS_TOKEN_KID,
                    "alg": self.algorithm,
                    "n": int_to_base64(public_numbers.n),
                    "e": int_to_base64(public_numbers.e),
                }
            ]
        }
