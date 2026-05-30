"""SMS delivery service for notification-service."""

import logging
import time
from datetime import datetime, timedelta, timezone

import pybreaker
from django.conf import settings
from django.utils import timezone as django_timezone

from apps.notifications.application.template_service import TemplateService
from apps.notifications.domain.models import (
    NotificationChannelChoices,
    NotificationMessageTypeChoices,
    NotificationStatusChoices,
)
from apps.notifications.domain.rules import PhoneNumberRule, sanitize_message_text
from apps.notifications.infrastructure.circuit_breakers import get_sms_circuit_breaker
from apps.notifications.infrastructure.providers.base import (
    InvalidSmsProviderError,
    SmsProviderError,
)
from apps.notifications.infrastructure.providers.factory import get_sms_provider
from apps.notifications.infrastructure.repositories import NotificationRepository

logger = logging.getLogger(__name__)


class SmsService:
    def __init__(self):
        self.repository = NotificationRepository()
        self.template_service = TemplateService()
        self.provider = None
        self.breaker = get_sms_circuit_breaker()
        self.retry_delays = self._parse_retry_delays(
            settings.SMS_OTP_RETRY_DELAYS_SECONDS
        )
        self.max_retries = settings.SMS_OTP_MAX_RETRIES
        self.template_service.ensure_default_otp_template()

    def _parse_retry_delays(self, value: str) -> list[int]:
        return [int(item.strip()) for item in value.split(",") if item.strip()]

    def _get_provider(self):
        if self.provider is None:
            self.provider = get_sms_provider()
        return self.provider

    def _current_provider_name(self) -> str:
        try:
            return self._get_provider().provider_name
        except InvalidSmsProviderError:
            return settings.SMS_PROVIDER

    def _build_request_payload(self, phone_number: str, message: str) -> dict:
        return {
            "phone_number": PhoneNumberRule.mask(phone_number),
            "message": sanitize_message_text(message),
        }

    def _build_otp_payload(
        self, phone_number: str, code: str, expires_in: int, purpose: str
    ) -> dict:
        template_code, rendered_message = self.template_service.render_otp_message(
            code=code,
            expires_in=expires_in,
        )
        return {
            "phone_number": PhoneNumberRule.mask(phone_number),
            "code": "******",
            "purpose": purpose,
            "expires_in": expires_in,
            "template_code": template_code,
            "message": rendered_message.replace(code, "******"),
        }

    def _parse_expires_at(self, occurred_at: str | None, expires_in: int):
        if occurred_at:
            parsed = datetime.fromisoformat(occurred_at)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed + timedelta(seconds=expires_in)
        return django_timezone.now() + timedelta(seconds=expires_in)

    def _call_provider(
        self, phone_number: str, message: str, code: str | None, expires_in: int | None
    ):
        provider = self._get_provider()
        if code is not None and expires_in is not None:
            return provider.send_otp(phone_number, code, expires_in)
        return provider.send_sms(phone_number, message)

    def _log_attempt(
        self,
        notification_message,
        request_payload: dict,
        response_payload: dict,
        is_success: bool,
        duration_ms: int,
        http_status_code: int | None = None,
    ):
        self.repository.create_delivery_log(
            notification_message=notification_message,
            provider=notification_message.provider,
            request_payload_masked=request_payload,
            response_payload=response_payload,
            http_status_code=http_status_code,
            is_success=is_success,
            duration_ms=duration_ms,
        )

    def send_sms(self, phone_number: str, message: str):
        normalized_phone = PhoneNumberRule.normalize(phone_number)
        if not normalized_phone:
            raise ValueError("Invalid phone number.")

        provider_name = self._current_provider_name()
        notification_message = self.repository.create_notification_message(
            channel=NotificationChannelChoices.SMS,
            message_type=NotificationMessageTypeChoices.REMINDER,
            recipient=normalized_phone,
            recipient_masked=PhoneNumberRule.mask(normalized_phone),
            provider=provider_name,
            status=NotificationStatusChoices.PENDING,
        )

        request_payload = self._build_request_payload(normalized_phone, message)
        return self._deliver_message(
            notification_message=notification_message,
            phone_number=normalized_phone,
            provider_callable=lambda: self._call_provider(
                normalized_phone, message, None, None
            ),
            request_payload=request_payload,
            code=None,
            expires_in=None,
            expires_at=None,
        )

    def send_otp(
        self,
        phone_number: str,
        code: str,
        expires_in: int,
        purpose: str = "login",
        occurred_at: str | None = None,
    ):
        normalized_phone = PhoneNumberRule.normalize(phone_number)
        if not normalized_phone:
            raise ValueError("Invalid phone number.")

        provider_name = self._current_provider_name()
        template_code, rendered_message = self.template_service.render_otp_message(
            code=code,
            expires_in=expires_in,
        )

        notification_message = self.repository.create_notification_message(
            channel=NotificationChannelChoices.SMS,
            message_type=NotificationMessageTypeChoices.OTP,
            recipient=normalized_phone,
            recipient_masked=PhoneNumberRule.mask(normalized_phone),
            template_code=template_code,
            provider=provider_name,
            status=NotificationStatusChoices.PENDING,
        )

        request_payload = self._build_otp_payload(
            normalized_phone,
            code=code,
            expires_in=expires_in,
            purpose=purpose,
        )
        expires_at = self._parse_expires_at(occurred_at, expires_in)

        return self._deliver_message(
            notification_message=notification_message,
            phone_number=normalized_phone,
            provider_callable=lambda: self._call_provider(
                normalized_phone,
                rendered_message,
                code,
                expires_in,
            ),
            request_payload=request_payload,
            code=code,
            expires_in=expires_in,
            expires_at=expires_at,
        )

    def handle_otp_command(self, payload: dict):
        if payload.get("event_type") != "SendOtpSmsRequested":
            raise ValueError("Unsupported event type.")

        data = payload.get("data", {})
        return self.send_otp(
            phone_number=data.get("phone_number"),
            code=data.get("code"),
            expires_in=int(data.get("expires_in", 120)),
            purpose=data.get("purpose", "login"),
            occurred_at=payload.get("occurred_at"),
        )

    def _deliver_message(
        self,
        notification_message,
        phone_number: str,
        provider_callable,
        request_payload: dict,
        code: str | None,
        expires_in: int | None,
        expires_at,
    ):
        attempts = self.max_retries + 1

        for attempt_index in range(attempts):
            if expires_at and django_timezone.now() >= expires_at:
                updated = self.repository.update_notification_message(
                    notification_message,
                    status=NotificationStatusChoices.SKIPPED,
                    error_code="OTP_EXPIRED",
                    error_message="OTP is no longer valid.",
                    retry_count=attempt_index,
                    last_attempt_at=django_timezone.now(),
                )
                self._log_attempt(
                    updated,
                    request_payload=request_payload,
                    response_payload={
                        "error_code": "OTP_EXPIRED",
                        "message": "OTP is no longer valid.",
                    },
                    is_success=False,
                    duration_ms=0,
                    http_status_code=None,
                )
                return updated

            now = django_timezone.now()
            self.repository.update_notification_message(
                notification_message,
                status=NotificationStatusChoices.SENDING,
                retry_count=attempt_index,
                last_attempt_at=now,
            )

            started_at = time.perf_counter()
            try:
                result = self.breaker.call(provider_callable)
                duration_ms = int((time.perf_counter() - started_at) * 1000)

                if result.success:
                    self._log_attempt(
                        notification_message,
                        request_payload=request_payload,
                        response_payload=result.raw_response or result.to_dict(),
                        is_success=True,
                        duration_ms=duration_ms,
                        http_status_code=200,
                    )
                    return self.repository.update_notification_message(
                        notification_message,
                        status=NotificationStatusChoices.SENT,
                        provider=result.provider,
                        provider_message_id=result.provider_message_id,
                        error_code=None,
                        error_message=None,
                        retry_count=attempt_index,
                        sent_at=django_timezone.now(),
                        last_attempt_at=django_timezone.now(),
                    )

                raise SmsProviderError(
                    result.error_code or "SMS_PROVIDER_FAILED",
                    result.error_message or "SMS provider failed to send the message.",
                )
            except pybreaker.CircuitBreakerError:
                duration_ms = int((time.perf_counter() - started_at) * 1000)
                failure_payload = {
                    "error_code": "SMS_CIRCUIT_OPEN",
                    "message": "SMS provider is temporarily unavailable.",
                }
                self._log_attempt(
                    notification_message,
                    request_payload=request_payload,
                    response_payload=failure_payload,
                    is_success=False,
                    duration_ms=duration_ms,
                    http_status_code=503,
                )
                if attempt_index >= self.max_retries:
                    return self.repository.update_notification_message(
                        notification_message,
                        status=NotificationStatusChoices.FAILED,
                        error_code="SMS_CIRCUIT_OPEN",
                        error_message="SMS provider is temporarily unavailable.",
                        retry_count=attempt_index,
                        last_attempt_at=django_timezone.now(),
                    )
            except InvalidSmsProviderError:
                duration_ms = int((time.perf_counter() - started_at) * 1000)
                failure_payload = {
                    "error_code": "INVALID_SMS_PROVIDER",
                    "message": "Configured SMS provider is not supported.",
                }
                self._log_attempt(
                    notification_message,
                    request_payload=request_payload,
                    response_payload=failure_payload,
                    is_success=False,
                    duration_ms=duration_ms,
                    http_status_code=500,
                )
                return self.repository.update_notification_message(
                    notification_message,
                    status=NotificationStatusChoices.FAILED,
                    error_code="INVALID_SMS_PROVIDER",
                    error_message="Configured SMS provider is not supported.",
                    retry_count=attempt_index,
                    last_attempt_at=django_timezone.now(),
                )
            except SmsProviderError as exc:
                duration_ms = int((time.perf_counter() - started_at) * 1000)
                failure_payload = {
                    "error_code": (
                        str(exc.args[0]) if exc.args else "SMS_PROVIDER_FAILED"
                    ),
                    "message": str(exc.args[1]) if len(exc.args) > 1 else str(exc),
                }
                self._log_attempt(
                    notification_message,
                    request_payload=request_payload,
                    response_payload=failure_payload,
                    is_success=False,
                    duration_ms=duration_ms,
                    http_status_code=502,
                )
                if attempt_index >= self.max_retries:
                    return self.repository.update_notification_message(
                        notification_message,
                        status=NotificationStatusChoices.FAILED,
                        error_code="SMS_PROVIDER_FAILED",
                        error_message="SMS provider failed to send the message.",
                        retry_count=attempt_index,
                        last_attempt_at=django_timezone.now(),
                    )

            if attempt_index < self.max_retries:
                notification_message = self.repository.update_notification_message(
                    notification_message,
                    status=NotificationStatusChoices.RETRY_PENDING,
                    retry_count=attempt_index + 1,
                    error_code="SMS_PROVIDER_FAILED",
                    error_message="SMS provider failed to send the message.",
                    last_attempt_at=django_timezone.now(),
                )
                delay = self.retry_delays[
                    min(attempt_index, len(self.retry_delays) - 1)
                ]
                if delay > 0:
                    time.sleep(delay)

        return self.repository.update_notification_message(
            notification_message,
            status=NotificationStatusChoices.FAILED,
            error_code="SMS_PROVIDER_FAILED",
            error_message="SMS provider failed to send the message.",
            retry_count=self.max_retries,
            last_attempt_at=django_timezone.now(),
        )
