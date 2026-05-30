"""SMS provider base types and abstract contract."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from apps.notifications.domain.value_objects import SmsSendResult


class InvalidSmsProviderError(Exception):
    """Raised when the configured SMS provider is unsupported."""


class SmsProviderError(Exception):
    """Generic SMS provider error."""


class SmsProvider(ABC):
    """Abstract SMS provider contract.

    Implementations must avoid returning or logging raw OTP values. Providers
    should return an instance of `SmsSendResult` describing the outcome.
    """

    provider_name: str = "unknown"

    @abstractmethod
    def send_sms(self, phone_number: str, message: str) -> SmsSendResult:
        raise NotImplementedError

    @abstractmethod
    def send_otp(self, phone_number: str, code: str, expires_in: int) -> SmsSendResult:
        raise NotImplementedError
