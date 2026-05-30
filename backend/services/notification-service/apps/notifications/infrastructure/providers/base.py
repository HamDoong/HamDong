"""Base classes and types for SMS providers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


class InvalidSmsProviderError(Exception):
    """Raised when requested SMS provider is not supported."""


class SmsProviderError(Exception):
    """Generic SMS provider error."""


@dataclass
class SmsSendResult:
    provider: str
    provider_message_id: Optional[str]
    success: bool
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    raw_response: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "provider_message_id": self.provider_message_id,
            "success": self.success,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "raw_response": self.raw_response,
        }


class SmsProvider:
    """Abstract SMS provider.

    Implementations MUST avoid returning or logging raw OTP values. Any
    payloads returned by providers should not include sensitive OTP codes.
    """

    provider_name: str = "unknown"

    def send_sms(self, phone_number: str, message: str) -> SmsSendResult:
        """Send a regular SMS message. Must be implemented by subclasses."""
        raise NotImplementedError()

    def send_otp(self, phone_number: str, code: str, expires_in: int) -> SmsSendResult:
        """Send an OTP SMS. Implementations should not store or return the raw code."""
        # default: render message externally and call send_sms; subclasses may override
        masked_message = "[otp hidden]"
        return self.send_sms(phone_number, masked_message)
"""SMS provider abstractions for notification-service."""

from abc import ABC, abstractmethod

from apps.notifications.domain.value_objects import SmsSendResult


class SmsProviderError(RuntimeError):
    """Raised when an SMS provider cannot complete a request."""


class InvalidSmsProviderError(SmsProviderError):
    """Raised when the configured provider is unsupported."""


class SmsProvider(ABC):
    """Abstract SMS provider contract."""

    provider_name: str = "unknown"

    @abstractmethod
    def send_sms(self, phone_number: str, message: str) -> SmsSendResult:
        raise NotImplementedError

    @abstractmethod
    def send_otp(self, phone_number: str, code: str, expires_in: int) -> SmsSendResult:
        raise NotImplementedError
