"""Redis OTP storage implementation."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import redis
from django.conf import settings

from apps.identity.domain.rules import OtpPurposeRule


class RedisOtpStore:
    """Manages OTP storage and retrieval in Redis with hashing."""

    _shared_client = None

    def __init__(self):
        if RedisOtpStore._shared_client is None:
            if str(getattr(settings, "REDIS_HOST", "")).lower() == "fakeredis":
                import fakeredis

                RedisOtpStore._shared_client = fakeredis.FakeStrictRedis(decode_responses=True)
            else:
                RedisOtpStore._shared_client = redis.Redis(
                    host=settings.REDIS_HOST,
                    port=settings.REDIS_PORT,
                    db=settings.REDIS_DB,
                    decode_responses=True,
                )
        self.redis_client = RedisOtpStore._shared_client

    @staticmethod
    def hash_otp(otp_code: str) -> str:
        return hashlib.sha256(otp_code.encode()).hexdigest()

    def _purpose_segment(self, purpose: str) -> str:
        if not OtpPurposeRule.is_valid(purpose):
            raise ValueError("INVALID_PURPOSE")
        return purpose.lower()

    def _otp_key(self, email: str, purpose: str) -> str:
        return f"otp:{self._purpose_segment(purpose)}:{email}"

    def _attempts_key(self, email: str, purpose: str) -> str:
        return f"otp:{self._purpose_segment(purpose)}:attempts:{email}"

    def _request_window_key(self, email: str, purpose: str) -> str:
        return f"otp:{self._purpose_segment(purpose)}:request_window:{email}"

    def _cooldown_key(self, email: str, purpose: str) -> str:
        return f"otp:{self._purpose_segment(purpose)}:cooldown:{email}"

    def store_otp(self, email: str, purpose: str, otp_code: str, ttl_seconds: int) -> None:
        otp_hash = self.hash_otp(otp_code)
        expires_at = (datetime.utcnow() + timedelta(seconds=ttl_seconds)).isoformat()
        otp_data = {"otp_hash": otp_hash, "expires_at": expires_at, "attempts": 0}
        self.redis_client.setex(self._otp_key(email, purpose), ttl_seconds, json.dumps(otp_data))

    def verify_otp(self, email: str, purpose: str, otp_code: str) -> bool:
        otp_data_str = self.redis_client.get(self._otp_key(email, purpose))
        if not otp_data_str:
            return False
        try:
            otp_data = json.loads(otp_data_str)
        except json.JSONDecodeError:
            return False
        otp_hash = self.hash_otp(otp_code)
        return otp_data["otp_hash"] == otp_hash

    def increment_verify_attempts(self, email: str, purpose: str) -> int:
        attempts = self.redis_client.incr(self._attempts_key(email, purpose))
        if attempts == 1:
            self.redis_client.expire(self._attempts_key(email, purpose), settings.OTP_TTL_SECONDS)
        return attempts

    def get_verify_attempts(self, email: str, purpose: str) -> int:
        attempts = self.redis_client.get(self._attempts_key(email, purpose))
        return int(attempts) if attempts else 0

    def reset_verify_attempts(self, email: str, purpose: str) -> None:
        self.redis_client.delete(self._attempts_key(email, purpose))

    def is_rate_limited(self, email: str, purpose: str) -> bool:
        count = self.redis_client.get(self._request_window_key(email, purpose))
        return int(count) >= settings.OTP_MAX_REQUESTS_PER_WINDOW if count else False

    def increment_request_count(self, email: str, purpose: str) -> int:
        count = self.redis_client.incr(self._request_window_key(email, purpose))
        if count == 1:
            self.redis_client.expire(self._request_window_key(email, purpose), settings.OTP_RATE_LIMIT_WINDOW_SECONDS)
        return count

    def get_request_count(self, email: str, purpose: str) -> int:
        count = self.redis_client.get(self._request_window_key(email, purpose))
        return int(count) if count else 0

    def get_cooldown_remaining(self, email: str, purpose: str) -> int:
        ttl = self.redis_client.ttl(self._cooldown_key(email, purpose))
        return max(0, ttl)

    def is_in_cooldown(self, email: str, purpose: str) -> bool:
        return self.redis_client.exists(self._cooldown_key(email, purpose)) > 0

    def set_cooldown(self, email: str, purpose: str, cooldown_seconds: int) -> None:
        self.redis_client.setex(self._cooldown_key(email, purpose), cooldown_seconds, "1")

    def delete_otp(self, email: str, purpose: str) -> None:
        self.redis_client.delete(self._otp_key(email, purpose))

    def get_otp_data(self, email: str, purpose: str) -> Optional[Dict[str, Any]]:
        otp_data_str = self.redis_client.get(self._otp_key(email, purpose))
        if not otp_data_str:
            return None
        try:
            return json.loads(otp_data_str)
        except json.JSONDecodeError:
            return None
