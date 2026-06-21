"""Fake email provider for local development and tests."""

from __future__ import annotations

import logging
import uuid

from apps.notifications.domain.rules import EmailRule, sanitize_message_text
from apps.notifications.domain.value_objects import EmailSendResult
from apps.notifications.infrastructure.providers.base import EmailProvider

logger = logging.getLogger(__name__)


class FakeEmailProvider(EmailProvider):
    provider_name = "fake"

    def send_email(self, email: str, subject: str, body: str) -> EmailSendResult:
        masked_email = EmailRule.mask(email)
        message_id = str(uuid.uuid4())
        logger.info(
            "Fake email sent to email=%s subject=%s body_preview=%s",
            masked_email,
            subject[:80],
            sanitize_message_text(body)[:120],
        )
        return EmailSendResult(
            success=True,
            provider=self.provider_name,
            provider_message_id=message_id,
            raw_response={
                "status": "sent",
                "provider": self.provider_name,
                "message_id": message_id,
            },
        )

    def send_otp(self, email: str, code: str, expires_in: int, subject: str, body: str) -> EmailSendResult:
        return self.send_email(email, subject=subject, body=body)


# Compatibility alias.
FakeSmsProvider = FakeEmailProvider
