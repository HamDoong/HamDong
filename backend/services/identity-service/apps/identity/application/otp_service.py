"""OTP generation and verification service."""

import random
import logging
from typing import Tuple, Optional

from django.conf import settings
from apps.identity.infrastructure.redis_otp_store import RedisOtpStore
from apps.identity.domain.rules import PhoneNumberRule

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
        """Generate a random OTP code."""
        return "".join(random.choices("0123456789", k=self.otp_length))

    def request_otp(
        self, phone_number: str
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Request OTP for phone number.

        Returns:
            Tuple of (success, error_code, debug_otp)
            - success: True if OTP was generated and stored
            - error_code: Error code if failed
            - debug_otp: OTP code if DEBUG and OTP_DEBUG_RETURN_CODE enabled
        """
        # Validate phone number
        if not PhoneNumberRule.is_valid(phone_number):
            return False, "INVALID_PHONE", None

        # Normalize phone number
        phone_number = PhoneNumberRule.normalize(phone_number)

        # Check rate limit
        if self.otp_store.is_rate_limited(phone_number):
            return False, "OTP_RATE_LIMITED", None

        # Check cooldown
        if self.otp_store.is_in_cooldown(phone_number):
            return False, "OTP_IN_COOLDOWN", None

        # Increment request counter
        self.otp_store.increment_request_count(phone_number)

        # Generate OTP
        otp_code = self.generate_otp()

        # Store OTP hash in Redis
        self.otp_store.store_otp(phone_number, otp_code, self.otp_ttl)

        # Set cooldown
        self.otp_store.set_cooldown(phone_number, self.resend_cooldown)

        logger.info(f"OTP requested for phone: {phone_number}")

        # Return OTP code only if debug mode is enabled
        debug_otp = None
        if settings.DEBUG and settings.OTP_DEBUG_RETURN_CODE:
            debug_otp = otp_code
            logger.debug(f"Debug OTP for {phone_number}: {otp_code}")

        return True, None, debug_otp

    def verify_otp(
        self, phone_number: str, otp_code: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Verify OTP code.

        Returns:
            Tuple of (success, error_code)
        """
        # Validate phone number
        if not PhoneNumberRule.is_valid(phone_number):
            return False, "INVALID_PHONE"

        # Normalize phone number
        phone_number = PhoneNumberRule.normalize(phone_number)

        # Check if OTP exists
        otp_data = self.otp_store.get_otp_data(phone_number)
        if not otp_data:
            return False, "OTP_EXPIRED"

        # Check attempts
        attempts = self.otp_store.get_verify_attempts(phone_number)
        if attempts >= self.max_verify_attempts:
            return False, "OTP_MAX_ATTEMPTS_EXCEEDED"

        # Verify OTP
        if not self.otp_store.verify_otp(phone_number, otp_code):
            self.otp_store.increment_verify_attempts(phone_number)
            return False, "INVALID_OTP"

        # Mark OTP as used
        self.otp_store.delete_otp(phone_number)
        self.otp_store.reset_verify_attempts(phone_number)

        logger.info(f"OTP verified for phone: {phone_number}")

        return True, None

    def get_resend_cooldown(self, phone_number: str) -> int:
        """Get remaining cooldown time in seconds."""
        if not PhoneNumberRule.is_valid(phone_number):
            return 0

        phone_number = PhoneNumberRule.normalize(phone_number)
        return self.otp_store.get_cooldown_remaining(phone_number)
