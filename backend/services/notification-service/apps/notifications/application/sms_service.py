"""Email delivery service for notification-service."""

from __future__ import annotations

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
from apps.notifications.domain.rules import EmailRule, sanitize_message_text
from apps.notifications.infrastructure.circuit_breakers import get_email_circuit_breaker
from apps.notifications.infrastructure.providers.base import (
    EmailProviderError,
    InvalidEmailProviderError,
)
from apps.notifications.infrastructure.providers.factory import get_email_provider
from apps.notifications.infrastructure.repositories import NotificationRepository

logger = logging.getLogger(__name__)


class EmailService:
    def __init__(self):
        self.repository = NotificationRepository()
        self.template_service = TemplateService()
        self.provider = None
        self.breaker = get_email_circuit_breaker()
        self.retry_delays = self._parse_retry_delays(
            settings.EMAIL_OTP_RETRY_DELAYS_SECONDS
        )
        self.max_retries = settings.EMAIL_OTP_MAX_RETRIES
        self.template_service.ensure_default_otp_template()

    def _parse_retry_delays(self, value: str) -> list[int]:
        return [int(item.strip()) for item in value.split(",") if item.strip()]

    def _get_provider(self):
        if self.provider is None:
            self.provider = get_email_provider()
        return self.provider

    def _current_provider_name(self) -> str:
        try:
            return self._get_provider().provider_name
        except InvalidEmailProviderError:
            return settings.EMAIL_PROVIDER

    def _build_request_payload(self, email: str, subject: str, body: str) -> dict:
        return {
            "email": EmailRule.mask(email),
            "subject": subject,
            "body_preview": sanitize_message_text(body)[:200],
        }

    def _build_otp_payload(
        self, email: str, code: str, expires_in: int, purpose: str
    ) -> dict:
        template_code, subject, rendered_message = self.template_service.render_otp_message(
            code=code,
            expires_in=expires_in,
        )
        return {
            "email": EmailRule.mask(email),
            "code": "******",
            "purpose": purpose,
            "expires_in": expires_in,
            "template_code": template_code,
            "subject": subject,
            "body_preview": sanitize_message_text(rendered_message.replace(code, "******"))[:200],
        }

    def _parse_expires_at(self, occurred_at: str | None, expires_in: int):
        if occurred_at:
            parsed = datetime.fromisoformat(occurred_at)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed + timedelta(seconds=expires_in)
        return django_timezone.now() + timedelta(seconds=expires_in)

    def _call_provider(
        self,
        email: str,
        subject: str,
        body: str,
        code: str | None,
        expires_in: int | None,
    ):
        provider = self._get_provider()
        if code is not None and expires_in is not None:
            return provider.send_otp(email, code, expires_in, subject, body)
        return provider.send_email(email, subject, body)

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

    def send_email(self, email: str, subject: str, body: str):
        normalized_email = EmailRule.normalize(email)
        if not normalized_email:
            raise ValueError("Invalid email.")

        provider_name = self._current_provider_name()
        notification_message = self.repository.create_notification_message(
            channel=NotificationChannelChoices.EMAIL,
            message_type=NotificationMessageTypeChoices.REMINDER,
            recipient=normalized_email,
            recipient_masked=EmailRule.mask(normalized_email),
            recipient_email=normalized_email,
            title=subject,
            body=body,
            metadata={},
            provider=provider_name,
            status=NotificationStatusChoices.PENDING,
        )

        request_payload = self._build_request_payload(normalized_email, subject, body)
        return self._deliver_message(
            notification_message=notification_message,
            email=normalized_email,
            subject=subject,
            body=body,
            request_payload=request_payload,
            code=None,
            expires_in=None,
        )

    def send_test_email(self, email: str, message: str):
        return self.send_email(email=email, subject="HamDong test email", body=message)

    def _deliver_message(
        self,
        *,
        notification_message,
        email: str,
        subject: str,
        body: str,
        request_payload: dict,
        code: str | None,
        expires_in: int | None,
    ):
        provider = self._current_provider_name()
        self.repository.update_notification_message(
            notification_message,
            status=NotificationStatusChoices.SENDING,
            provider=provider,
            last_attempt_at=django_timezone.now(),
        )

        for attempt in range(self.max_retries + 1):
            started = time.perf_counter()
            try:
                result = self.breaker.call(
                    self._call_provider,
                    email,
                    subject,
                    body,
                    code,
                    expires_in,
                )
                duration_ms = int((time.perf_counter() - started) * 1000)
                self._log_attempt(
                    notification_message,
                    request_payload=request_payload,
                    response_payload=result.to_dict(),
                    is_success=result.success,
                    duration_ms=duration_ms,
                )
                if result.success:
                    return self.repository.update_notification_message(
                        notification_message,
                        status=NotificationStatusChoices.SENT,
                        provider=result.provider,
                        provider_message_id=result.provider_message_id,
                        sent_at=django_timezone.now(),
                        retry_count=attempt,
                        error_code=None,
                        error_message=None,
                        last_error=None,
                        last_attempt_at=django_timezone.now(),
                    )
                raise EmailProviderError(result.error_code or "EMAIL_PROVIDER_FAILED")
            except (EmailProviderError, InvalidEmailProviderError, pybreaker.CircuitBreakerError) as exc:
                duration_ms = int((time.perf_counter() - started) * 1000)
                if isinstance(exc, pybreaker.CircuitBreakerError):
                    error_code = "EMAIL_CIRCUIT_OPEN"
                elif isinstance(exc, InvalidEmailProviderError):
                    error_code = "INVALID_EMAIL_PROVIDER"
                else:
                    error_code = "EMAIL_PROVIDER_FAILED"
                self._log_attempt(
                    notification_message,
                    request_payload=request_payload,
                    response_payload={"error": error_code},
                    is_success=False,
                    duration_ms=duration_ms,
                )
                if attempt >= self.max_retries:
                    return self.repository.update_notification_message(
                        notification_message,
                        status=NotificationStatusChoices.FAILED,
                        retry_count=attempt,
                        error_code=error_code,
                        error_message=str(exc),
                        last_error=str(exc),
                        last_attempt_at=django_timezone.now(),
                    )
                delay = self.retry_delays[min(attempt, len(self.retry_delays) - 1)] if self.retry_delays else 0
                if delay:
                    time.sleep(delay)

    def handle_otp_command(self, payload: dict):
        data = payload.get("data") or {}

        normalized_email = EmailRule.normalize(data.get("email"))
        if not normalized_email:
            raise ValueError("INVALID_EMAIL")

        code = data["code"]
        expires_in = int(data["expires_in"])

        template_code, subject, body = self.template_service.render_otp_message(
            code=code,
            expires_in=expires_in,
        )

        metadata = {
            "purpose": data.get("purpose", "login"),
            "expires_in": expires_in,
            "event_id": payload.get("event_id"),
        }

        provider_name = self._current_provider_name()

        # Never persist the raw OTP code in the database.
        stored_body = sanitize_message_text(body)

        notification_message = self.repository.create_notification_message(
            recipient_user_id=None,
            recipient_email=normalized_email,
            channel=NotificationChannelChoices.EMAIL,
            message_type=NotificationMessageTypeChoices.OTP,
            title=subject,
            body=stored_body,
            metadata=metadata,
            recipient=normalized_email,
            recipient_masked=EmailRule.mask(normalized_email),
            template_code=template_code,
            provider=provider_name,
            status=NotificationStatusChoices.PENDING,
        )

        request_payload = self._build_otp_payload(
            normalized_email,
            code,
            expires_in,
            data.get("purpose", "login"),
        )

        expires_at = self._parse_expires_at(
            payload.get("occurred_at"),
            expires_in,
        )

        if django_timezone.now() >= expires_at:
            error_message = "OTP expired before email delivery."

            notification_message = self.repository.update_notification_message(
                notification_message,
                status=NotificationStatusChoices.SKIPPED,
                error_code="OTP_EXPIRED",
                error_message=error_message,
                last_error=error_message,
                last_attempt_at=django_timezone.now(),
            )

            self._log_attempt(
                notification_message,
                request_payload=request_payload,
                response_payload={"error": "OTP_EXPIRED"},
                is_success=False,
                duration_ms=0,
            )

            return notification_message

        return self._deliver_message(
            notification_message=notification_message,
            email=normalized_email,
            subject=subject,
            body=body,
            request_payload=request_payload,
            code=code,
            expires_in=expires_in,
        )

# Compatibility alias.
SmsService = EmailService
