"""Kavenegar SMS provider adapter."""

from __future__ import annotations

import logging
import uuid
from typing import Any, Dict

import httpx
from django.conf import settings

from apps.notifications.domain.rules import PhoneNumberRule
from apps.notifications.domain.value_objects import SmsSendResult
from apps.notifications.infrastructure.clients import create_http_client
from apps.notifications.infrastructure.providers.base import SmsProvider

logger = logging.getLogger(__name__)


class KavenegarSmsProvider(SmsProvider):
    provider_name = "kavenegar"

    def send_sms(self, phone_number: str, message: str) -> SmsSendResult:
        if not settings.SMS_API_KEY or not settings.SMS_SENDER:
            return SmsSendResult(
                success=False,
                provider=self.provider_name,
                error_code="SMS_PROVIDER_FAILED",
                error_message="Missing Kavenegar credentials.",
                raw_response={"error": "missing_credentials"},
            )

        masked_phone = PhoneNumberRule.mask(phone_number)
        payload = {
            "sender": settings.SMS_SENDER,
            "receptor": phone_number,
            "message": message,
        }

        try:
            with create_http_client() as client:
                response = client.post(
                    f"https://api.kavenegar.com/v1/{settings.SMS_API_KEY}/sms/send.json",
                    data=payload,
                )

            raw_response = response.json() if response.content else {}
            # httpx's response.is_success is not always present in older clients
            success = getattr(response, "is_success", None)
            if success is None:
                success = 200 <= response.status_code < 300

            if success:
                provider_message_id = str(
                    raw_response.get("return", {}).get("messageid") or uuid.uuid4()
                )
                logger.info("Kavenegar SMS sent to phone_number=%s", masked_phone)
                return SmsSendResult(
                    success=True,
                    provider=self.provider_name,
                    provider_message_id=provider_message_id,
                    raw_response=raw_response,
                )

            return SmsSendResult(
                success=False,
                provider=self.provider_name,
                error_code="SMS_PROVIDER_FAILED",
                error_message="Kavenegar rejected the message.",
                raw_response=raw_response,
            )
        except httpx.HTTPError as exc:
            return SmsSendResult(
                success=False,
                provider=self.provider_name,
                error_code="SMS_PROVIDER_FAILED",
                error_message=str(exc),
                raw_response={"error": str(exc)},
            )

    def send_otp(self, phone_number: str, code: str, expires_in: int) -> SmsSendResult:
        # Do not return or log the OTP; providers should not leak codes in responses.
        message = f"{code}\nاعتبار: {expires_in} ثانیه"
        return self.send_sms(phone_number, message)
