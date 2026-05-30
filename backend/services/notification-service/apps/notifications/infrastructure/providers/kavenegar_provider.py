"""Adapter for Kavenegar SMS provider.

This adapter uses `httpx` to call the Kavenegar API. It expects
`KAVENEGAR_API_KEY` in Django settings.
"""

from __future__ import annotations

import httpx
import time
from typing import Dict, Any

from django.conf import settings

from apps.notifications.infrastructure.providers.base import (
    SmsProvider,
    SmsSendResult,
    SmsProviderError,
)


class KavenegarSmsProvider(SmsProvider):
    provider_name = "kavenegar"

    def __init__(self) -> None:
        self.api_key = getattr(settings, "KAVENEGAR_API_KEY", None)
        self.base_url = getattr(
            settings, "KAVENEGAR_API_URL", "https://api.kavenegar.com/v1"
        )
        if not self.api_key:
            raise SmsProviderError("MISSING_API_KEY", "Kavenegar API key is not configured")

    def _build_url(self, path: str) -> str:
        return f"{self.base_url}/{self.api_key}/{path}.json"

    def send_sms(self, phone_number: str, message: str) -> SmsSendResult:
        url = self._build_url("sms/send")
        payload = {"receptor": phone_number, "message": message}
        started = time.perf_counter()
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(url, data=payload)
            duration_ms = int((time.perf_counter() - started) * 1000)
            raw = None
            try:
                raw = resp.json()
            except Exception:
                raw = {"text": resp.text}

            if resp.status_code in (200, 201):
                # Kavenegar returns a result array; extract id if present
                provider_message_id = None
                if isinstance(raw, dict) and raw.get("return"):
                    provider_message_id = str(raw["return"].get("messageid") or raw["return"].get("id"))
                return SmsSendResult(
                    provider=self.provider_name,
                    provider_message_id=provider_message_id,
                    success=True,
                    raw_response={"status_code": resp.status_code, "body": raw, "duration_ms": duration_ms},
                )

            return SmsSendResult(
                provider=self.provider_name,
                provider_message_id=None,
                success=False,
                error_code=str(resp.status_code),
                error_message=str(raw),
                raw_response={"status_code": resp.status_code, "body": raw, "duration_ms": duration_ms},
            )
        except Exception as exc:
            raise SmsProviderError("HTTP_ERROR", str(exc))
"""Kavenegar SMS provider adapter."""

import logging
import uuid

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
            if response.is_success:
                provider_message_id = str(
                    raw_response.get("return", {}).get("messageid") or uuid.uuid4()
                )
                logger.info(
                    "Kavenegar SMS sent to phone_number=%s",
                    masked_phone,
                )
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
        message = f"{code}\nاعتبار: {expires_in} ثانیه"
        return self.send_sms(phone_number, message)
