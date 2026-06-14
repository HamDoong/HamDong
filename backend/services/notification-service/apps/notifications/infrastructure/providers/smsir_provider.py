"""Legacy compatibility wrapper for the retired Sms.ir SMS provider."""

from __future__ import annotations

from apps.notifications.domain.value_objects import EmailSendResult
from apps.notifications.infrastructure.providers.base import EmailProvider


class SmsIrEmailProvider(EmailProvider):
    provider_name = "smsir"

    def send_email(self, recipient_email: str, subject: str, body: str) -> EmailSendResult:
        return EmailSendResult(
            success=False,
            provider=self.provider_name,
            error_code="EMAIL_PROVIDER_DISABLED",
            error_message="SMS.ir is not supported after the email migration. Configure EMAIL_PROVIDER=smtp or EMAIL_PROVIDER=fake.",
            raw_response={"error": "provider_disabled"},
        )


# Backwards-compatible alias retained for old imports.
SmsIrSmsProvider = SmsIrEmailProvider
