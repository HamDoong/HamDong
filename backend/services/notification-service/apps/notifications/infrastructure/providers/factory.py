"""Factory to select and instantiate SMS providers based on settings."""

from __future__ import annotations

from django.conf import settings

from apps.notifications.infrastructure.providers.base import (
    InvalidSmsProviderError,
)
from apps.notifications.infrastructure.providers.fake_provider import FakeSmsProvider


def get_sms_provider(provider_name: str | None = None):
    """Return an instance of the configured SMS provider.

    If `provider_name` is None, `settings.SMS_PROVIDER` is used.
    Raises `InvalidSmsProviderError` for unsupported providers.
    """
    name = provider_name or getattr(settings, "SMS_PROVIDER", "fake")
    name = name.lower()

    if name == "fake":
        return FakeSmsProvider()

    if name == "kavenegar":
        from apps.notifications.infrastructure.providers.kavenegar_provider import (
            KavenegarSmsProvider,
        )

        return KavenegarSmsProvider()

    if name == "melipayamak":
        from apps.notifications.infrastructure.providers.melipayamak_provider import (
            MelipayamakSmsProvider,
        )

        return MelipayamakSmsProvider()

    raise InvalidSmsProviderError(f"Unsupported SMS provider: {name}")
"""SMS provider factory."""

from django.conf import settings

from apps.notifications.infrastructure.providers.base import InvalidSmsProviderError
from apps.notifications.infrastructure.providers.fake_provider import FakeSmsProvider
from apps.notifications.infrastructure.providers.kavenegar_provider import (
    KavenegarSmsProvider,
)
from apps.notifications.infrastructure.providers.melipayamak_provider import (
    MelipayamakSmsProvider,
)


def get_sms_provider(provider_name: str | None = None):
    provider = (provider_name or settings.SMS_PROVIDER or "fake").lower()

    if provider == "fake":
        return FakeSmsProvider()

    if provider == "kavenegar":
        return KavenegarSmsProvider()

    if provider == "melipayamak":
        return MelipayamakSmsProvider()

    raise InvalidSmsProviderError("Configured SMS provider is not supported.")
