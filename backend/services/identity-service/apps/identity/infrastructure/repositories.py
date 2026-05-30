"""Database repositories for identity-service."""

import hashlib
from typing import Optional
from datetime import timedelta

from django.utils import timezone
from apps.identity.domain.models import User, RefreshToken


class UserRepository:
    """Repository for User model operations."""

    @staticmethod
    def create(phone_number: str, **kwargs) -> User:
        """Create a new user."""
        return User.objects.create(phone_number=phone_number, **kwargs)

    @staticmethod
    def get_by_phone(phone_number: str) -> Optional[User]:
        """Get user by phone number."""
        return User.objects.filter(
            phone_number=phone_number, deleted_at__isnull=True
        ).first()

    @staticmethod
    def get_by_id(user_id: str) -> Optional[User]:
        """Get user by ID."""
        return User.objects.filter(id=user_id, deleted_at__isnull=True).first()

    @staticmethod
    def update(user: User, **kwargs) -> User:
        """Update user fields."""
        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)
        user.version += 1
        user.save()
        return user


class RefreshTokenRepository:
    """Repository for RefreshToken model operations."""

    @staticmethod
    def hash_token(token: str) -> str:
        """Hash refresh token."""
        return hashlib.sha256(token.encode()).hexdigest()

    @staticmethod
    def create(
        user: User, token_hash: str, jti: str, lifetime_seconds: int, **kwargs
    ) -> RefreshToken:
        """Create a new refresh token."""
        expires_at = timezone.now() + timedelta(seconds=lifetime_seconds)
        return RefreshToken.objects.create(
            user=user,
            token_hash=token_hash,
            jti=jti,
            expires_at=expires_at,
            **kwargs,
        )

    @staticmethod
    def get_by_token_hash(token_hash: str) -> Optional[RefreshToken]:
        """Get refresh token by hash."""
        return RefreshToken.objects.filter(
            token_hash=token_hash,
            revoked_at__isnull=True,
        ).first()

    @staticmethod
    def get_by_jti(jti: str) -> Optional[RefreshToken]:
        """Get refresh token by JTI."""
        return RefreshToken.objects.filter(jti=jti, revoked_at__isnull=True).first()

    @staticmethod
    def revoke(refresh_token: RefreshToken) -> RefreshToken:
        """Revoke a refresh token."""
        refresh_token.revoked_at = timezone.now()
        refresh_token.save()
        return refresh_token

    @staticmethod
    def is_expired(refresh_token: RefreshToken) -> bool:
        """Check if refresh token is expired."""
        return timezone.now() > refresh_token.expires_at

    @staticmethod
    def get_active_tokens(user: User):
        """Get all active (non-revoked, non-expired) tokens for user."""
        return RefreshToken.objects.filter(
            user=user,
            revoked_at__isnull=True,
            expires_at__gt=timezone.now(),
        )
