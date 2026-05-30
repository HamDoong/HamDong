"""Domain events for notification-service."""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict


class DomainEvent:
    """Base domain event contract."""

    def __init__(
        self,
        event_id: str,
        event_type: str,
        occurred_at: datetime,
        version: int,
        data: Dict[str, Any],
    ):
        self.event_id = event_id
        self.event_type = event_type
        self.occurred_at = occurred_at
        self.version = version
        self.data = data

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "occurred_at": self.occurred_at.isoformat(),
            "version": self.version,
            "data": self.data,
        }


class SendOtpSmsRequested(DomainEvent):
    """Command event for OTP SMS delivery."""

    def __init__(
        self,
        phone_number: str,
        code: str,
        purpose: str = "login",
        expires_in: int = 120,
    ):
        super().__init__(
            event_id=str(uuid.uuid4()),
            event_type="SendOtpSmsRequested",
            occurred_at=datetime.now(timezone.utc),
            version=1,
            data={
                "phone_number": phone_number,
                "code": code,
                "purpose": purpose,
                "expires_in": expires_in,
            },
        )


"""Domain events for notification-service."""
