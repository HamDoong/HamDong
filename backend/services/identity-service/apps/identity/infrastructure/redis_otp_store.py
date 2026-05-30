"""Redis OTP storage implementation."""

import hashlib
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

import redis
from django.conf import settings


class RedisOtpStore:
    """Manages OTP storage and retrieval in Redis with hashing."""

    def __init__(self):
        self.redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            decode_responses=True,
        )

    @staticmethod
    def hash_otp(otp_code: str) -> str:
        """Hash OTP code using SHA256."""
        return hashlib.sha256(otp_code.encode()).hexdigest()

    def store_otp(self, phone_number: str, otp_code: str, ttl_seconds: int) -> None:
        """
        Store hashed OTP in Redis.

        Args:
            phone_number: User's phone number
            otp_code: OTP code to store (will be hashed)
            ttl_seconds: Time to live in seconds
        """
        otp_hash = self.hash_otp(otp_code)
        expires_at = (datetime.utcnow() + timedelta(seconds=ttl_seconds)).isoformat()

        otp_data = {
            "otp_hash": otp_hash,
            "expires_at": expires_at,
            "attempts": 0,
        }

        key = f"otp:login:{phone_number}"
        self.redis_client.setex(key, ttl_seconds, json.dumps(otp_data))

    def verify_otp(self, phone_number: str, otp_code: str) -> bool:
        """
        Verify OTP code.

        Args:
            phone_number: User's phone number
            otp_code: OTP code to verify

        Returns:
            True if OTP is valid, False otherwise
        """
        key = f"otp:login:{phone_number}"
        otp_data_str = self.redis_client.get(key)

        if not otp_data_str:
            return False

        try:
            otp_data = json.loads(otp_data_str)
        except json.JSONDecodeError:
            return False

        otp_hash = self.hash_otp(otp_code)
        return otp_data["otp_hash"] == otp_hash

    def increment_verify_attempts(self, phone_number: str) -> int:
        """Increment verify attempts counter."""
        key = f"otp:login:attempts:{phone_number}"
        attempts = self.redis_client.incr(key)
        # Set expiry if first increment
        if attempts == 1:
            self.redis_client.expire(key, settings.OTP_TTL_SECONDS)
        return attempts

    def get_verify_attempts(self, phone_number: str) -> int:
        """Get current verify attempts count."""
        key = f"otp:login:attempts:{phone_number}"
        attempts = self.redis_client.get(key)
        return int(attempts) if attempts else 0

    def reset_verify_attempts(self, phone_number: str) -> None:
        """Reset verify attempts after successful verification."""
        key = f"otp:login:attempts:{phone_number}"
        self.redis_client.delete(key)

    def is_rate_limited(self, phone_number: str) -> bool:
        """Check if phone number is rate limited for OTP requests."""
        key = f"otp:login:request_window:{phone_number}"
        count = self.redis_client.get(key)
        return int(count) >= settings.OTP_MAX_REQUESTS_PER_WINDOW if count else False

    def increment_request_count(self, phone_number: str) -> int:
        """Increment OTP request count for rate limiting."""
        key = f"otp:login:request_window:{phone_number}"
        count = self.redis_client.incr(key)
        # Set expiry if first request
        if count == 1:
            self.redis_client.expire(key, settings.OTP_RATE_LIMIT_WINDOW_SECONDS)
        return count

    def get_request_count(self, phone_number: str) -> int:
        """Get current request count in rate limit window."""
        key = f"otp:login:request_window:{phone_number}"
        count = self.redis_client.get(key)
        return int(count) if count else 0

    def get_cooldown_remaining(self, phone_number: str) -> int:
        """Get remaining cooldown time in seconds."""
        key = f"otp:login:cooldown:{phone_number}"
        ttl = self.redis_client.ttl(key)
        return max(0, ttl)

    def is_in_cooldown(self, phone_number: str) -> bool:
        """Check if phone number is in cooldown period."""
        key = f"otp:login:cooldown:{phone_number}"
        return self.redis_client.exists(key) > 0

    def set_cooldown(self, phone_number: str, cooldown_seconds: int) -> None:
        """Set cooldown period for OTP requests."""
        key = f"otp:login:cooldown:{phone_number}"
        self.redis_client.setex(key, cooldown_seconds, "1")

    def delete_otp(self, phone_number: str) -> None:
        """Delete OTP after successful verification."""
        key = f"otp:login:{phone_number}"
        self.redis_client.delete(key)

    def get_otp_data(self, phone_number: str) -> Optional[Dict[str, Any]]:
        """Get OTP data (for testing purposes)."""
        key = f"otp:login:{phone_number}"
        otp_data_str = self.redis_client.get(key)

        if not otp_data_str:
            return None

        try:
            return json.loads(otp_data_str)
        except json.JSONDecodeError:
            return None
