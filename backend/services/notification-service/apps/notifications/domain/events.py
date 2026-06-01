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
        source_service: str = "notification-service",
        routing_key: str | None = None,
        correlation_id: str | None = None,
        causation_id: str | None = None,
    ):
        self.event_id = event_id
        self.event_type = event_type
        self.occurred_at = occurred_at
        self.version = version
        self.data = data
        self.source_service = source_service
        self.routing_key = routing_key
        self.correlation_id = correlation_id
        self.causation_id = causation_id

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "event_version": self.version,
            "occurred_at": self.occurred_at.isoformat(),
            "version": self.version,
            "source_service": self.source_service,
            "routing_key": self.routing_key,
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
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
            source_service="identity-service",
            data={
                "phone_number": phone_number,
                "code": code,
                "purpose": purpose,
                "expires_in": expires_in,
            },
        )


"""Domain events for notification-service."""
