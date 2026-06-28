"""Password reset and session management services."""

from __future__ import annotations

import hmac
import logging
import secrets
from datetime import timedelta
from ipaddress import ip_address as parse_ip_address
from typing import Optional

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from apps.identity.application.user_service import UserService
from apps.identity.domain.events import PasswordResetCompleted, SendOtpEmailRequested
from apps.identity.domain.models import PasswordResetChallenge, PasswordResetToken, RefreshToken, User
from apps.identity.domain.rules import EmailRule
from apps.identity.infrastructure.rabbitmq_publisher import RabbitMqPublisher
from apps.identity.infrastructure.redis_otp_store import RedisOtpStore
from apps.identity.infrastructure.repositories import (
    PasswordResetChallengeRepository,
    PasswordResetTokenRepository,
    RefreshTokenRepository,
    UserRepository,
)

logger = logging.getLogger(__name__)


class PasswordResetThrottle:
    """Redis-backed cooldown and rate limiting for forgot-password requests."""

    def __init__(self) -> None:
        self.redis_client = RedisOtpStore().redis_client
        self.cooldown_seconds = int(getattr(settings, "OTP_RESEND_COOLDOWN_SECONDS", 60))
        self.max_requests_per_window = int(getattr(settings, "OTP_MAX_REQUESTS_PER_WINDOW", 3))
        self.window_seconds = int(getattr(settings, "OTP_RATE_LIMIT_WINDOW_SECONDS", 600))

    @staticmethod
    def _namespace(email: str) -> str:
        return f"password_reset:{email}"

    def _cooldown_key(self, email: str) -> str:
        return f"{self._namespace(email)}:cooldown"

    def _window_key(self, email: str) -> str:
        return f"{self._namespace(email)}:request_window"

    def is_in_cooldown(self, email: str) -> bool:
        return self.redis_client.exists(self._cooldown_key(email)) > 0

    def get_cooldown_remaining(self, email: str) -> int:
        ttl = self.redis_client.ttl(self._cooldown_key(email))
        return max(0, ttl)

    def is_rate_limited(self, email: str) -> bool:
        count = self.redis_client.get(self._window_key(email))
        return int(count) >= self.max_requests_per_window if count else False

    def record_request(self, email: str) -> None:
        count = self.redis_client.incr(self._window_key(email))
        if count == 1:
            self.redis_client.expire(self._window_key(email), self.window_seconds)
        self.redis_client.setex(self._cooldown_key(email), self.cooldown_seconds, "1")


class PasswordResetService:
    """Encapsulates password-reset challenge, verification, and completion logic."""

    def __init__(self) -> None:
        self.publisher = RabbitMqPublisher()
        self.user_service = UserService()
        self.throttle = PasswordResetThrottle()
        self.otp_length = int(getattr(settings, "OTP_LENGTH", 6))
        self.otp_ttl_seconds = int(getattr(settings, "PASSWORD_RESET_OTP_TTL_SECONDS", 600))
        self.max_attempts = int(getattr(settings, "OTP_MAX_VERIFY_ATTEMPTS", 5))
        self.reset_token_ttl_seconds = int(getattr(settings, "PASSWORD_RESET_TOKEN_TTL_SECONDS", 600))

    def generate_otp(self) -> str:
        return "".join(secrets.choice("0123456789") for _ in range(self.otp_length))

    def generate_reset_token(self) -> str:
        return secrets.token_urlsafe(32)

    def request_reset(self, email: str) -> tuple[bool, str | None, str | None]:
        normalized_email = EmailRule.normalize(email)
        if not normalized_email:
            return False, "INVALID_EMAIL", None

        if self.throttle.is_rate_limited(normalized_email):
            return False, "OTP_RATE_LIMITED", None

        if self.throttle.is_in_cooldown(normalized_email):
            return False, "OTP_IN_COOLDOWN", None

        self.throttle.record_request(normalized_email)

        user = UserRepository.get_by_email(normalized_email)
        if not user or not user.is_active:
            logger.info("Password reset requested for email=%s", EmailRule.mask(normalized_email))
            return True, None, None

        raw_otp = self.generate_otp()
        otp_hash = PasswordResetChallengeRepository.hash_secret(raw_otp)
        expires_at = timezone.now() + timedelta(seconds=self.otp_ttl_seconds)

        with transaction.atomic():
            PasswordResetChallengeRepository.expire_open_challenges(normalized_email)
            PasswordResetTokenRepository.invalidate_open_tokens_for_user(user)
            PasswordResetChallengeRepository.create(
                user=user,
                email=normalized_email,
                otp_hash=otp_hash,
                expires_at=expires_at,
                max_attempts=self.max_attempts,
            )
            event = SendOtpEmailRequested(
                email=normalized_email,
                code=raw_otp,
                purpose="PASSWORD_RESET",
                expires_in=self.otp_ttl_seconds,
            )
            self.publisher.publish(event.to_dict(), "identity.otp.requested")

        debug_otp = raw_otp if settings.DEBUG and getattr(settings, "OTP_DEBUG_RETURN_CODE", False) else None
        logger.info("Password reset challenge created for email=%s", EmailRule.mask(normalized_email))
        return True, None, debug_otp

    def verify_otp(self, email: str, otp_code: str) -> tuple[bool, str | None, dict | None]:
        normalized_email = EmailRule.normalize(email)
        if not normalized_email:
            return False, "INVALID_EMAIL", None

        challenge = PasswordResetChallengeRepository.latest_for_email(normalized_email)
        if not challenge:
            return False, "INVALID_OTP", None

        now = timezone.now()

        if challenge.used_at or challenge.status == PasswordResetChallenge.StatusChoices.USED:
            return False, "OTP_ALREADY_USED", None
        if challenge.status == PasswordResetChallenge.StatusChoices.LOCKED:
            return False, "OTP_MAX_ATTEMPTS_EXCEEDED", None
        if challenge.status == PasswordResetChallenge.StatusChoices.EXPIRED or now >= challenge.expires_at:
            if challenge.status != PasswordResetChallenge.StatusChoices.EXPIRED:
                challenge.status = PasswordResetChallenge.StatusChoices.EXPIRED
                PasswordResetChallengeRepository.save(challenge, update_fields=["status"])
            return False, "OTP_EXPIRED", None
        if challenge.status == PasswordResetChallenge.StatusChoices.VERIFIED:
            return False, "OTP_ALREADY_USED", None

        provided_hash = PasswordResetChallengeRepository.hash_secret(otp_code)
        if not hmac.compare_digest(challenge.otp_hash, provided_hash):
            challenge.attempt_count += 1
            update_fields = ["attempt_count"]
            if challenge.attempt_count >= challenge.max_attempts:
                challenge.status = PasswordResetChallenge.StatusChoices.LOCKED
                update_fields.append("status")
            PasswordResetChallengeRepository.save(challenge, update_fields=update_fields)
            return False, "INVALID_OTP", None

        reset_token = self.generate_reset_token()
        reset_token_hash = PasswordResetTokenRepository.hash_secret(reset_token)
        expires_at = now + timedelta(seconds=self.reset_token_ttl_seconds)

        with transaction.atomic():
            PasswordResetTokenRepository.invalidate_open_tokens_for_user(challenge.user)
            PasswordResetTokenRepository.create(
                challenge=challenge,
                user=challenge.user,
                token_hash=reset_token_hash,
                expires_at=expires_at,
            )
            challenge.status = PasswordResetChallenge.StatusChoices.VERIFIED
            challenge.verified_at = now
            PasswordResetChallengeRepository.save(challenge, update_fields=["status", "verified_at"])

        return True, None, {
            "reset_token": reset_token,
            "expires_in_seconds": self.reset_token_ttl_seconds,
        }

    def reset_password(
        self,
        *,
        reset_token: str,
        new_password: str,
        new_password_confirm: str,
    ) -> tuple[bool, str | None]:
        if new_password != new_password_confirm:
            return False, "PASSWORD_CONFIRMATION_MISMATCH"

        token_hash = PasswordResetTokenRepository.hash_secret(reset_token)
        token_obj = PasswordResetTokenRepository.get_any_by_token_hash(token_hash)
        if not token_obj:
            return False, "INVALID_RESET_TOKEN"
        if token_obj.used_at:
            return False, "RESET_TOKEN_USED"
        if timezone.now() >= token_obj.expires_at:
            return False, "RESET_TOKEN_EXPIRED"

        user = UserRepository.get_active_by_id(token_obj.user_id)
        if not user:
            return False, "INVALID_RESET_TOKEN"

        try:
            self.user_service.validate_new_password(user, new_password)
        except ValueError as exc:
            return False, str(exc)

        with transaction.atomic():
            user.set_password(new_password)
            user.version += 1
            user.save(update_fields=["password_hash", "password_changed_at", "version", "updated_at"])
            RefreshTokenRepository.revoke_active_for_user(user)
            PasswordResetTokenRepository.mark_used(token_obj)
            challenge = token_obj.challenge
            challenge.status = PasswordResetChallenge.StatusChoices.USED
            challenge.used_at = timezone.now()
            PasswordResetChallengeRepository.save(challenge, update_fields=["status", "used_at"])
            event = PasswordResetCompleted(
                user_id=user.id,
                completed_at=user.password_changed_at.isoformat() if user.password_changed_at else timezone.now().isoformat(),
            )
            self.publisher.publish(event.to_dict(), "identity.user.password_reset_completed")

        logger.info("Password reset completed for email=%s", EmailRule.mask(user.email))
        return True, None


class SessionService:
    """User session listing and revocation helpers backed by refresh tokens."""

    def list_sessions(self, *, user: User, current_jti: str | None = None) -> list[dict]:
        sessions = RefreshTokenRepository.list_active_sessions(user)
        return [self.serialize_session(session, current_jti=current_jti) for session in sessions]

    def serialize_session(self, session: RefreshToken, *, current_jti: str | None = None) -> dict:
        return {
            "id": str(session.id),
            "remember_me": bool(getattr(session, "remember_me", False)),
            "created_at": session.created_at,
            "last_used_at": session.last_used_at,
            "expires_at": session.expires_at,
            "is_current": bool(current_jti and str(session.jti) == str(current_jti)),
            "user_agent": session.user_agent,
            "ip_address": self.mask_ip(session.ip_address),
        }

    def revoke_session(self, *, user: User, session_id: str) -> bool:
        session = RefreshTokenRepository.get_any_by_id_for_user(session_id, user)
        if not session:
            return False
        if not session.is_revoked:
            RefreshTokenRepository.revoke(session)
        return True

    def revoke_other_sessions(self, *, user: User, current_jti: str | None = None) -> int:
        return RefreshTokenRepository.revoke_other_active_for_user(user, current_jti=current_jti)

    @staticmethod
    def mask_ip(value: str | None) -> str | None:
        if not value:
            return None
        try:
            parsed = parse_ip_address(value)
        except ValueError:
            return None
        if parsed.version == 4:
            parts = value.split(".")
            return ".".join(parts[:3] + ["0"])
        pieces = parsed.exploded.split(":")
        return ":".join(pieces[:4] + ["****"] * 4)
