"""A simple fake SMS provider for local development and testing."""

from __future__ import annotations

import uuid
import time
from typing import Dict

from apps.notifications.infrastructure.providers.base import SmsProvider, SmsSendResult


class FakeSmsProvider(SmsProvider):
    provider_name = "fake"

    def send_sms(self, phone_number: str, message: str) -> SmsSendResult:
        # Simulate latency
        time.sleep(0.01)
        provider_message_id = str(uuid.uuid4())
        raw_response: Dict[str, str] = {
            "status": "ok",
            "message": "queued",
            "id": provider_message_id,
        }
        return SmsSendResult(
            provider=self.provider_name,
            provider_message_id=provider_message_id,
            success=True,
            raw_response=raw_response,
        )

    def send_otp(self, phone_number: str, code: str, expires_in: int) -> SmsSendResult:
        # Do NOT include the raw OTP in any returned payload.
        return self.send_sms(phone_number, f"OTP hidden (expires in {expires_in}s)")
"""Fake SMS provider for local development and tests."""

import logging
import uuid

from apps.notifications.domain.rules import PhoneNumberRule, sanitize_message_text
from apps.notifications.domain.value_objects import SmsSendResult
from apps.notifications.infrastructure.providers.base import SmsProvider

logger = logging.getLogger(__name__)


class FakeSmsProvider(SmsProvider):
    provider_name = "fake"

    def send_sms(self, phone_number: str, message: str) -> SmsSendResult:
        masked_phone = PhoneNumberRule.mask(phone_number)
        safe_message = sanitize_message_text(message)
        message_id = str(uuid.uuid4())
        logger.info(
            "Fake SMS sent to phone_number=%s message_preview=%s",
            masked_phone,
            safe_message[:80],
        )
        return SmsSendResult(
            success=True,
            provider=self.provider_name,
            provider_message_id=message_id,
            raw_response={
                "status": "sent",
                "provider": self.provider_name,
                "message_id": message_id,
            },
        )

    def send_otp(self, phone_number: str, code: str, expires_in: int) -> SmsSendResult:
        message = f"OTP code sent to {PhoneNumberRule.mask(phone_number)}"
        return self.send_sms(phone_number, message)
