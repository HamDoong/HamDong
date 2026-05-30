"""JWT token generation and verification service."""

import uuid
from datetime import datetime, timedelta, timezone as tz
from typing import Tuple, Dict, Any, Optional

import jwt
from django.conf import settings

from apps.identity.infrastructure.key_loader import JwtKeyLoader
from apps.identity.domain.models import User
from apps.identity.infrastructure.repositories import RefreshTokenRepository


class TokenService:
    """Service for JWT token operations."""

    def __init__(self):
        self.algorithm = settings.JWT_ALGORITHM
        self.issuer = settings.JWT_ISSUER
        self.audience = settings.JWT_AUDIENCE
        self.access_token_lifetime = settings.JWT_ACCESS_TOKEN_LIFETIME_SECONDS
        self.refresh_token_lifetime = settings.JWT_REFRESH_TOKEN_LIFETIME_SECONDS
        self.private_key = JwtKeyLoader.get_private_key()
        self.public_key = JwtKeyLoader.get_public_key()

    def generate_tokens(
        self, user: User, user_agent: str = None, ip_address: str = None
    ) -> Tuple[str, str, str]:
        """
        Generate access and refresh tokens for a user.

        Args:
            user: User instance
            user_agent: User agent string
            ip_address: IP address

        Returns:
            Tuple of (access_token, refresh_token, jti)
        """
        # Generate new JTI
        jti = str(uuid.uuid4())

        # Create access token
        access_token = self._create_access_token(user, jti)

        # Create refresh token
        refresh_token, refresh_token_hash = self._create_refresh_token(user, jti)

        # Store refresh token hash in database
        RefreshTokenRepository.create(
            user=user,
            token_hash=refresh_token_hash,
            jti=jti,
            lifetime_seconds=self.refresh_token_lifetime,
            user_agent=user_agent,
            ip_address=ip_address,
        )

        return access_token, refresh_token, jti

    def _create_access_token(self, user: User, jti: str) -> str:
        """Create access token."""
        now = datetime.now(tz.utc)
        expires_at = now + timedelta(seconds=self.access_token_lifetime)

        payload = {
            "sub": str(user.id),
            "phone_number": user.phone_number,
            "role": user.role,
            "type": "access",
            "jti": jti,
            "iat": int(now.timestamp()),
            "exp": int(expires_at.timestamp()),
            "iss": self.issuer,
            "aud": self.audience,
        }

        return jwt.encode(payload, self.private_key, algorithm=self.algorithm)

    def _create_refresh_token(self, user: User, jti: str) -> Tuple[str, str]:
        """Create refresh token and return both token and hash."""
        now = datetime.now(tz.utc)
        expires_at = now + timedelta(seconds=self.refresh_token_lifetime)

        payload = {
            "sub": str(user.id),
            "type": "refresh",
            "jti": jti,
            "iat": int(now.timestamp()),
            "exp": int(expires_at.timestamp()),
            "iss": self.issuer,
            "aud": self.issuer,  # Refresh tokens are for identity service only
        }

        token = jwt.encode(payload, self.private_key, algorithm=self.algorithm)
        token_hash = RefreshTokenRepository.hash_token(token)

        return token, token_hash

    def verify_access_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify and decode access token.

        Args:
            token: JWT token to verify

        Returns:
            Decoded payload if valid, None otherwise
        """
        try:
            payload = jwt.decode(
                token,
                self.public_key,
                algorithms=[self.algorithm],
                audience=self.audience,
                issuer=self.issuer,
            )

            if payload.get("type") != "access":
                return None

            return payload
        except jwt.InvalidTokenError:
            return None

    def verify_refresh_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify and decode refresh token.

        Args:
            token: JWT token to verify

        Returns:
            Decoded payload if valid, None otherwise
        """
        try:
            payload = jwt.decode(
                token,
                self.public_key,
                algorithms=[self.algorithm],
                audience=self.issuer,
                issuer=self.issuer,
            )

            if payload.get("type") != "refresh":
                return None

            # Check if token exists and is not revoked
            token_hash = RefreshTokenRepository.hash_token(token)
            db_token = RefreshTokenRepository.get_by_token_hash(token_hash)

            if not db_token:
                return None

            if db_token.is_revoked:
                return None

            if RefreshTokenRepository.is_expired(db_token):
                return None

            return payload
        except jwt.InvalidTokenError:
            return None

    def refresh_tokens(
        self, refresh_token: str, user_agent: str = None, ip_address: str = None
    ) -> Optional[Tuple[str, str]]:
        """
        Refresh access token using refresh token.

        Args:
            refresh_token: Valid refresh token
            user_agent: User agent string
            ip_address: IP address

        Returns:
            Tuple of (new_access_token, new_refresh_token) if successful, None otherwise
        """
        # Verify refresh token
        payload = self.verify_refresh_token(refresh_token)
        if not payload:
            return None

        # Get user
        user_id = payload.get("sub")
        user = User.objects.filter(id=user_id, deleted_at__isnull=True).first()
        if not user:
            return None

        # Get old token from database
        token_hash = RefreshTokenRepository.hash_token(refresh_token)
        old_token = RefreshTokenRepository.get_by_token_hash(token_hash)
        if not old_token:
            return None

        # Revoke old token
        RefreshTokenRepository.revoke(old_token)

        # Generate new tokens
        access_token, new_refresh_token, jti = self.generate_tokens(
            user,
            user_agent=user_agent,
            ip_address=ip_address,
        )

        return access_token, new_refresh_token

    def get_jwks(self) -> Dict[str, Any]:
        """
        Get JWKS (JSON Web Key Set) for public key.

        Returns:
            JWKS dict suitable for public endpoint
        """
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.backends import default_backend
        import base64

        # Load public key
        public_key_obj = serialization.load_pem_public_key(
            self.public_key.encode(),
            backend=default_backend(),
        )

        # Extract RSA public numbers
        public_numbers = public_key_obj.public_numbers()

        # Convert to base64 url-safe
        n = public_numbers.n
        e = public_numbers.e

        def int_to_base64(val):
            bytes_val = val.to_bytes((val.bit_length() + 7) // 8, "big")
            return base64.urlsafe_b64encode(bytes_val).rstrip(b"=").decode("utf-8")

        return {
            "keys": [
                {
                    "kty": "RSA",
                    "use": "sig",
                    "alg": self.algorithm,
                    "n": int_to_base64(n),
                    "e": int_to_base64(e),
                    "kid": "identity-service-key",
                }
            ]
        }
