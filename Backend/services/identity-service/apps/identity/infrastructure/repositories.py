"""Database repositories for identity-service."""

from __future__ import annotations

import hashlib
from datetime import timedelta
from typing import Optional

from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from apps.identity.domain.models import (
    OutboxMessage,
    OutboxMessageStatusChoices,
    PasswordResetChallenge,
    PasswordResetToken,
    RefreshToken,
    User,
    UserBankCard,
)


class UserRepository:
    """Repository for User model operations."""

    @staticmethod
    def create(email: str, **kwargs) -> User:
        return User.objects.create(email=email, **kwargs)

    @staticmethod
    def get_by_email(email: str) -> Optional[User]:
        return User.objects.filter(
            email=email,
            deleted_at__isnull=True,
        ).first()

    @staticmethod
    def get_any_by_email(email: str) -> Optional[User]:
        return User.objects.filter(email=email).first()

    @staticmethod
    def get_by_art_name(art_name: str) -> Optional[User]:
        return User.objects.filter(
            art_name=art_name,
            deleted_at__isnull=True,
        ).first()

    @staticmethod
    def get_by_phone_number(phone_number: str) -> Optional[User]:
        return User.objects.filter(
            phone_number=phone_number,
            deleted_at__isnull=True,
        ).first()

    @staticmethod
    def get_by_id(user_id: str) -> Optional[User]:
        return User.objects.filter(id=user_id, deleted_at__isnull=True).first()

    @staticmethod
    def get_active_by_id(user_id: str) -> Optional[User]:
        return User.objects.filter(id=user_id, deleted_at__isnull=True, is_active=True).first()

    @staticmethod
    def update(user: User, **kwargs) -> User:
        update_fields = []
        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)
                update_fields.append(key)
        if not update_fields:
            return user
        user.version += 1
        update_fields.extend(["version", "updated_at"])
        user.save(update_fields=update_fields)
        return user


class RefreshTokenRepository:
    """Repository for RefreshToken model operations."""

    @staticmethod
    def hash_token(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    @staticmethod
    def create(
        user: User,
        token_hash: str,
        jti: str,
        lifetime_seconds: int,
        *,
        remember_me: bool = False,
        **kwargs,
    ) -> RefreshToken:
        now = timezone.now()
        expires_at = now + timedelta(seconds=lifetime_seconds)
        return RefreshToken.objects.create(
            user=user,
            token_hash=token_hash,
            jti=jti,
            remember_me=remember_me,
            expires_at=expires_at,
            last_used_at=now,
            **kwargs,
        )

    @staticmethod
    def get_by_token_hash(token_hash: str) -> Optional[RefreshToken]:
        return RefreshToken.objects.filter(
            token_hash=token_hash,
            revoked_at__isnull=True,
        ).first()

    @staticmethod
    def get_by_jti(jti: str) -> Optional[RefreshToken]:
        return RefreshToken.objects.filter(jti=jti, revoked_at__isnull=True).first()

    @staticmethod
    def get_any_by_token_hash(token_hash: str) -> Optional[RefreshToken]:
        return RefreshToken.objects.filter(token_hash=token_hash).first()

    @staticmethod
    def get_any_by_id_for_user(session_id: str, user: User) -> Optional[RefreshToken]:
        return RefreshToken.objects.filter(id=session_id, user=user).first()

    @staticmethod
    def list_active_sessions(user: User):
        now = timezone.now()
        return RefreshToken.objects.filter(
            user=user,
            revoked_at__isnull=True,
            expires_at__gt=now,
        ).order_by("-created_at")

    @staticmethod
    def touch(refresh_token: RefreshToken) -> RefreshToken:
        refresh_token.last_used_at = timezone.now()
        refresh_token.save(update_fields=["last_used_at", "updated_at"])
        return refresh_token

    @staticmethod
    def revoke(refresh_token: RefreshToken) -> RefreshToken:
        refresh_token.revoked_at = timezone.now()
        refresh_token.save(update_fields=["revoked_at", "updated_at"])
        return refresh_token

    @staticmethod
    def revoke_active_for_user(user: User):
        now = timezone.now()
        return RefreshToken.objects.filter(
            user=user,
            revoked_at__isnull=True,
            expires_at__gt=now,
        ).update(revoked_at=now, updated_at=now)

    @staticmethod
    def revoke_other_active_for_user(user: User, current_jti: str | None = None) -> int:
        now = timezone.now()
        filters = Q(user=user, revoked_at__isnull=True, expires_at__gt=now)
        if current_jti:
            filters &= ~Q(jti=current_jti)
        return RefreshToken.objects.filter(filters).update(revoked_at=now, updated_at=now)

    @staticmethod
    def is_expired(refresh_token: RefreshToken) -> bool:
        return timezone.now() > refresh_token.expires_at

    @staticmethod
    def get_active_tokens(user: User):
        return RefreshToken.objects.filter(
            user=user,
            revoked_at__isnull=True,
            expires_at__gt=timezone.now(),
        )


class PasswordResetChallengeRepository:
    @staticmethod
    def hash_secret(raw_value: str) -> str:
        return hashlib.sha256(raw_value.encode()).hexdigest()

    @staticmethod
    def expire_open_challenges(email: str) -> int:
        now = timezone.now()
        return PasswordResetChallenge.objects.filter(
            email=email,
            status__in=[
                PasswordResetChallenge.StatusChoices.PENDING,
                PasswordResetChallenge.StatusChoices.VERIFIED,
            ],
        ).update(
            status=PasswordResetChallenge.StatusChoices.EXPIRED,
            updated_at=now,
        )

    @staticmethod
    def create(*, user: User | None, email: str, otp_hash: str, expires_at, max_attempts: int) -> PasswordResetChallenge:
        return PasswordResetChallenge.objects.create(
            user=user,
            email=email,
            otp_hash=otp_hash,
            expires_at=expires_at,
            max_attempts=max_attempts,
        )

    @staticmethod
    def latest_for_email(email: str) -> Optional[PasswordResetChallenge]:
        return PasswordResetChallenge.objects.filter(email=email).order_by("-created_at").first()

    @staticmethod
    def save(challenge: PasswordResetChallenge, *, update_fields: list[str]) -> PasswordResetChallenge:
        challenge.save(update_fields=update_fields + ["updated_at"])
        return challenge


class PasswordResetTokenRepository:
    @staticmethod
    def hash_secret(raw_value: str) -> str:
        return hashlib.sha256(raw_value.encode()).hexdigest()

    @staticmethod
    def invalidate_open_tokens_for_user(user: User) -> int:
        now = timezone.now()
        return PasswordResetToken.objects.filter(
            user=user,
            used_at__isnull=True,
        ).update(used_at=now, updated_at=now)

    @staticmethod
    def create(*, challenge: PasswordResetChallenge, user: User, token_hash: str, expires_at) -> PasswordResetToken:
        return PasswordResetToken.objects.create(
            challenge=challenge,
            user=user,
            token_hash=token_hash,
            expires_at=expires_at,
        )

    @staticmethod
    def get_any_by_token_hash(token_hash: str) -> Optional[PasswordResetToken]:
        return PasswordResetToken.objects.filter(token_hash=token_hash).select_related("user", "challenge").first()

    @staticmethod
    def mark_used(reset_token: PasswordResetToken) -> PasswordResetToken:
        reset_token.used_at = timezone.now()
        reset_token.save(update_fields=["used_at", "updated_at"])
        return reset_token


class OutboxRepository:
    @staticmethod
    def create(*, event_type, routing_key, payload, exchange, source_service="identity-service"):
        return OutboxMessage.objects.create(
            event_id=payload["event_id"],
            event_type=event_type,
            event_version=int(payload.get("event_version", 1)),
            source_service=source_service,
            exchange=exchange,
            routing_key=routing_key,
            payload=payload,
        )

    @staticmethod
    def pending(limit: int = 50, max_retry_count: int = 5):
        return OutboxMessage.objects.filter(
            status__in=[OutboxMessageStatusChoices.PENDING, OutboxMessageStatusChoices.FAILED],
            retry_count__lt=max_retry_count,
            available_at__lte=timezone.now(),
        ).order_by("created_at")[:limit]

    @staticmethod
    def mark_published(message):
        message.status = OutboxMessageStatusChoices.PUBLISHED
        message.published_at = timezone.now()
        message.last_error = None
        message.save(update_fields=["status", "published_at", "last_error", "updated_at"])

    @staticmethod
    def mark_failed(message, error: str):
        message.retry_count += 1
        message.last_error = error
        max_retry_count = int(getattr(settings, "EVENT_MAX_RETRY_COUNT", 5))
        retry_delays = [
            int(value.strip())
            for value in str(getattr(settings, "EVENT_RETRY_DELAY_SECONDS", "10,30,60")).split(",")
            if value.strip()
        ]
        if hasattr(message, "available_at") and message.retry_count <= len(retry_delays):
            message.available_at = timezone.now() + timedelta(seconds=retry_delays[message.retry_count - 1])
        if message.retry_count >= max_retry_count:
            message.status = OutboxMessageStatusChoices.FAILED
        else:
            message.status = OutboxMessageStatusChoices.PENDING
        update_fields = ["retry_count", "last_error", "status", "updated_at"]
        if hasattr(message, "available_at"):
            update_fields.append("available_at")
        message.save(update_fields=update_fields)
