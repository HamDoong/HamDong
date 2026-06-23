"""OTP generation and verification service."""

from __future__ import annotations

import logging
import random
from typing import Optional, Tuple

from django.conf import settings

from apps.identity.domain.rules import EmailRule, OtpPurposeRule
from apps.identity.infrastructure.redis_otp_store import RedisOtpStore

logger = logging.getLogger(__name__)


class OtpService:
    """Service for OTP operations."""

    def __init__(self):
        self.otp_store = RedisOtpStore()
        self.otp_length = settings.OTP_LENGTH
        self.otp_ttl = settings.OTP_TTL_SECONDS
        self.resend_cooldown = settings.OTP_RESEND_COOLDOWN_SECONDS
        self.max_verify_attempts = settings.OTP_MAX_VERIFY_ATTEMPTS
        self.max_requests_per_window = settings.OTP_MAX_REQUESTS_PER_WINDOW
        self.rate_limit_window = settings.OTP_RATE_LIMIT_WINDOW_SECONDS

    def generate_otp(self) -> str:
        return "".join(random.choices("0123456789", k=self.otp_length))

    def request_otp(self, email: str, purpose: object) -> Tuple[bool, Optional[str], Optional[str], Optional[str]]:
        if not OtpPurposeRule.is_valid(purpose):
            return False, "INVALID_PURPOSE", None, None

        normalized_email = EmailRule.normalize(email)
        if not normalized_email:
            return False, "INVALID_EMAIL", None, None

        if self.otp_store.is_rate_limited(normalized_email, purpose):
            return False, "OTP_RATE_LIMITED", None, None

        if self.otp_store.is_in_cooldown(normalized_email, purpose):
            return False, "OTP_IN_COOLDOWN", None, None

        self.otp_store.increment_request_count(normalized_email, purpose)
        otp_code = self.generate_otp()
        self.otp_store.store_otp(normalized_email, purpose, otp_code, self.otp_ttl)
        self.otp_store.set_cooldown(normalized_email, purpose, self.resend_cooldown)

        logger.info("OTP requested for email=%s", EmailRule.mask(normalized_email))

        debug_otp = None
        if settings.DEBUG and settings.OTP_DEBUG_RETURN_CODE:
            debug_otp = otp_code

        return True, None, otp_code, debug_otp

    def verify_otp(self, email: str, otp_code: str, purpose: object) -> Tuple[bool, Optional[str]]:
        if not OtpPurposeRule.is_valid(purpose):
            return False, "INVALID_PURPOSE"

        normalized_email = EmailRule.normalize(email)
        if not normalized_email:
            return False, "INVALID_EMAIL"

        otp_data = self.otp_store.get_otp_data(normalized_email, purpose)
        if not otp_data:
            return False, "OTP_EXPIRED"

        attempts = self.otp_store.get_verify_attempts(normalized_email, purpose)
        if attempts >= self.max_verify_attempts:
            return False, "OTP_MAX_ATTEMPTS_EXCEEDED"

        if not self.otp_store.verify_otp(normalized_email, purpose, otp_code):
            self.otp_store.increment_verify_attempts(normalized_email, purpose)
            return False, "INVALID_OTP"

        self.otp_store.delete_otp(normalized_email, purpose)
        self.otp_store.reset_verify_attempts(normalized_email, purpose)

        logger.info("OTP verified for email=%s", EmailRule.mask(normalized_email))
        return True, None

    def get_resend_cooldown(self, email: str, purpose: object) -> int:
        if not OtpPurposeRule.is_valid(purpose):
            return 0
        normalized_email = EmailRule.normalize(email)
        if not normalized_email:
            return 0
        return self.otp_store.get_cooldown_remaining(normalized_email, purpose)
