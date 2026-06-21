"""Legacy compatibility wrapper for the retired Melipayamak SMS provider."""

from __future__ import annotations

from apps.notifications.domain.value_objects import EmailSendResult
from apps.notifications.infrastructure.providers.base import EmailProvider


class MelipayamakEmailProvider(EmailProvider):
    provider_name = "melipayamak"

    def send_email(self, recipient_email: str, subject: str, body: str) -> EmailSendResult:
        return EmailSendResult(
            success=False,
            provider=self.provider_name,
            error_code="EMAIL_PROVIDER_DISABLED",
            error_message="Melipayamak is not supported after the email migration. Configure EMAIL_PROVIDER=smtp or EMAIL_PROVIDER=fake.",
            raw_response={"error": "provider_disabled"},
        )


# Backwards-compatible alias retained for old imports.
MelipayamakSmsProvider = MelipayamakEmailProvider
