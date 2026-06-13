"""SMS provider factory."""

from __future__ import annotations

from django.conf import settings

from apps.notifications.infrastructure.providers.base import InvalidSmsProviderError
from apps.notifications.infrastructure.providers.fake_provider import FakeSmsProvider


def get_sms_provider(provider_name: str | None = None):
    """Return an instance of the configured SMS provider.

    If `provider_name` is None, `settings.SMS_PROVIDER` is used. Lazily imports
    provider implementations to avoid importing HTTP client dependencies at
    module import time.
    """
    provider = (provider_name or settings.SMS_PROVIDER or "fake").lower()

    if provider == "fake":
        return FakeSmsProvider()

    if provider == "kavenegar":
        from apps.notifications.infrastructure.providers.kavenegar_provider import (
            KavenegarSmsProvider,
        )

        return KavenegarSmsProvider()

    if provider == "melipayamak":
        from apps.notifications.infrastructure.providers.melipayamak_provider import (
            MelipayamakSmsProvider,
        )

        return MelipayamakSmsProvider()

    raise InvalidSmsProviderError(f"Unsupported SMS provider: {provider}")
