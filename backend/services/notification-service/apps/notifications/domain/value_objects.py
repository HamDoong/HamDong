"""Value objects for notification-service."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Optional


@dataclass(slots=True)
class EmailSendResult:
    success: bool
    provider: str
    provider_message_id: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    raw_response: Any = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class OtpEmailCommand:
    email: str
    code: str
    purpose: str
    expires_in: int
