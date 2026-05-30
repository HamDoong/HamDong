"""Adapter for Melipayamak SMS provider."""

from __future__ import annotations

import httpx
import time
from typing import Any, Dict

from django.conf import settings

from apps.notifications.infrastructure.providers.base import (
    SmsProvider,
    SmsSendResult,
    SmsProviderError,
)


class MelipayamakSmsProvider(SmsProvider):
    provider_name = "melipayamak"

    def __init__(self) -> None:
        self.username = getattr(settings, "MELIPAYAMAK_USERNAME", None)
        self.password = getattr(settings, "MELIPAYAMAK_PASSWORD", None)
        self.base_url = getattr(
            settings, "MELIPAYAMAK_API_URL", "https://api.payamak-panel.com/post/"
        )
        if not (self.username and self.password):
            raise SmsProviderError("MISSING_CREDENTIALS", "Melipayamak credentials not configured")

    def send_sms(self, phone_number: str, message: str) -> SmsSendResult:
        url = self.base_url
        payload = {
            "username": self.username,
            "password": self.password,
            "to": phone_number,
            "from": getattr(settings, "MELIPAYAMAK_FROM", "30005000"),
            "text": message,
        }
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
                provider_message_id = None
                # melipayamak may return an integer id or dict
                try:
                    if isinstance(raw, dict) and raw.get("messageid"):
                        provider_message_id = str(raw.get("messageid"))
                except Exception:
                    provider_message_id = None

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
"""Melipayamak SMS provider adapter."""

import logging
import uuid

import httpx
from django.conf import settings

from apps.notifications.domain.rules import PhoneNumberRule
from apps.notifications.domain.value_objects import SmsSendResult
from apps.notifications.infrastructure.clients import create_http_client
from apps.notifications.infrastructure.providers.base import SmsProvider

logger = logging.getLogger(__name__)


class MelipayamakSmsProvider(SmsProvider):
    provider_name = "melipayamak"

    def send_sms(self, phone_number: str, message: str) -> SmsSendResult:
        if not settings.SMS_API_KEY or not settings.SMS_SENDER:
            return SmsSendResult(
                success=False,
                provider=self.provider_name,
                error_code="SMS_PROVIDER_FAILED",
                error_message="Missing Melipayamak credentials.",
                raw_response={"error": "missing_credentials"},
            )

        masked_phone = PhoneNumberRule.mask(phone_number)
        payload = {
            "username": settings.SMS_API_KEY,
            "to": phone_number,
            "from": settings.SMS_SENDER,
            "text": message,
        }

        try:
            with create_http_client() as client:
                response = client.post(
                    "https://rest.payamak-panel.com/api/SendSMS/SendSms",
                    data=payload,
                )

            raw_response = response.json() if response.content else {}
            if response.is_success:
                provider_message_id = str(
                    raw_response.get("RetStr")
                    or raw_response.get("Value")
                    or uuid.uuid4()
                )
                logger.info(
                    "Melipayamak SMS sent to phone_number=%s",
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
                error_message="Melipayamak rejected the message.",
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
