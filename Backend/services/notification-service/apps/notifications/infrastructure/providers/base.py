"""Email provider base types and abstract contract."""

from __future__ import annotations

from abc import ABC, abstractmethod

from apps.notifications.domain.value_objects import EmailSendResult


class InvalidEmailProviderError(Exception):
    """Raised when the configured email provider is unsupported."""


class EmailProviderError(Exception):
    """Generic email provider error."""


class EmailProvider(ABC):
    provider_name: str = "unknown"

    @abstractmethod
    def send_email(self, email: str, subject: str, body: str) -> EmailSendResult:
        raise NotImplementedError

    @abstractmethod
    def send_otp(self, email: str, code: str, expires_in: int, subject: str, body: str) -> EmailSendResult:
        raise NotImplementedError


# Compatibility aliases for older imports.
InvalidSmsProviderError = InvalidEmailProviderError
SmsProviderError = EmailProviderError
SmsProvider = EmailProvider
