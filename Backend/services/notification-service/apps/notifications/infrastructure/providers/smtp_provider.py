"""SMTP email provider for notification-service."""

from __future__ import annotations

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection

from apps.notifications.domain.value_objects import EmailSendResult
from apps.notifications.infrastructure.providers.base import EmailProvider, EmailProviderError


class SmtpEmailProvider(EmailProvider):
    provider_name = "smtp"

    def __init__(self):
        self.connection = get_connection(
            backend=settings.EMAIL_BACKEND,
            host=settings.EMAIL_HOST,
            port=settings.EMAIL_PORT,
            username=settings.EMAIL_HOST_USER,
            password=settings.EMAIL_HOST_PASSWORD,
            use_tls=settings.EMAIL_USE_TLS,
            use_ssl=settings.EMAIL_USE_SSL,
            timeout=settings.EMAIL_TIMEOUT_SECONDS,
        )

    def send_email(self, email: str, subject: str, body: str) -> EmailSendResult:
        try:
            message = EmailMultiAlternatives(
                subject=subject,
                body=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[email],
                connection=self.connection,
            )
            sent = message.send(fail_silently=False)
        except Exception as exc:  # pragma: no cover - exercised by tests via mocking
            raise EmailProviderError("EMAIL_PROVIDER_FAILED") from exc

        return EmailSendResult(
            success=bool(sent),
            provider=self.provider_name,
            provider_message_id=message.extra_headers.get("Message-ID") if hasattr(message, "extra_headers") else None,
            raw_response={"sent_count": sent},
        )

    def send_otp(self, email: str, code: str, expires_in: int, subject: str, body: str) -> EmailSendResult:
        return self.send_email(email, subject=subject, body=body)
