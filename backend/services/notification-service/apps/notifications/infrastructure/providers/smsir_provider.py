"""SMS.ir provider adapter."""

from __future__ import annotations

import logging
import uuid

import httpx
from django.conf import settings

from apps.notifications.domain.rules import PhoneNumberRule
from apps.notifications.domain.value_objects import SmsSendResult
from apps.notifications.infrastructure.clients import create_http_client
from apps.notifications.infrastructure.providers.base import SmsProvider

logger = logging.getLogger(__name__)


class SmsIrSmsProvider(SmsProvider):
    provider_name = "smsir"

    def _format_mobile_for_smsir(self, phone_number: str) -> str:
        normalized = PhoneNumberRule.normalize(phone_number)
        if not normalized:
            return phone_number

        # sms.ir verify examples use 9xxxxxxxxx format.
        if normalized.startswith("0"):
            return normalized[1:]

        return normalized

    def send_sms(self, phone_number: str, message: str) -> SmsSendResult:
        return SmsSendResult(
            success=False,
            provider=self.provider_name,
            error_code="SMS_PROVIDER_FAILED",
            error_message="SMS.ir simple SMS is not configured yet. Use OTP verify flow.",
            raw_response={"error": "simple_sms_not_supported"},
        )

    def send_otp(self, phone_number: str, code: str, expires_in: int) -> SmsSendResult:
        if not settings.SMS_API_KEY:
            return SmsSendResult(
                success=False,
                provider=self.provider_name,
                error_code="SMS_PROVIDER_FAILED",
                error_message="Missing SMS.ir API key.",
                raw_response={"error": "missing_api_key"},
            )

        if not settings.SMSIR_TEMPLATE_ID:
            return SmsSendResult(
                success=False,
                provider=self.provider_name,
                error_code="SMS_PROVIDER_FAILED",
                error_message="Missing SMS.ir template id.",
                raw_response={"error": "missing_template_id"},
            )

        mobile = self._format_mobile_for_smsir(phone_number)
        masked_phone = PhoneNumberRule.mask(phone_number)

        payload = {
            "mobile": mobile,
            "templateId": int(settings.SMSIR_TEMPLATE_ID),
            "parameters": [
                {
                    "name": settings.SMSIR_TEMPLATE_PARAMETER_NAME,
                    "value": str(code),
                }
            ],
        }

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "x-api-key": settings.SMS_API_KEY,
        }

        try:
            with create_http_client() as client:
                response = client.post(
                    settings.SMSIR_VERIFY_URL,
                    json=payload,
                    headers=headers,
                )

            raw_response = response.json() if response.content else {}

            http_success = 200 <= response.status_code < 300
            api_success = raw_response.get("status") == 1

            if http_success and api_success:
                data = raw_response.get("data") or {}
                provider_message_id = str(
                    data.get("messageId")
                    or data.get("messageID")
                    or uuid.uuid4()
                )

                logger.info("SMS.ir OTP sent to phone_number=%s", masked_phone)

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
                error_message=raw_response.get("message", "SMS.ir rejected the message."),
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
        except ValueError as exc:
            return SmsSendResult(
                success=False,
                provider=self.provider_name,
                error_code="SMS_PROVIDER_FAILED",
                error_message=str(exc),
                raw_response={"error": str(exc)},
            )