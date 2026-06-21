"""Email provider factory."""

from __future__ import annotations

from django.conf import settings

from apps.notifications.infrastructure.providers.base import InvalidEmailProviderError
from apps.notifications.infrastructure.providers.fake_provider import FakeEmailProvider
from apps.notifications.infrastructure.providers.smtp_provider import SmtpEmailProvider


def get_email_provider(provider_name: str | None = None):
    provider = (provider_name or settings.EMAIL_PROVIDER or "fake").lower()

    if provider == "fake":
        return FakeEmailProvider()

    if provider == "smtp":
        return SmtpEmailProvider()

    raise InvalidEmailProviderError(f"Unsupported email provider: {provider}")


# Backwards-compatible alias.
get_sms_provider = get_email_provider
