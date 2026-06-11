"""Domain events for notification-service."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from apps.notifications.infrastructure.event_envelope import build_event_envelope


ROUTING_KEYS = {
    "NotificationSent": "notification.sent",
    "NotificationFailed": "notification.failed",
    "SmsSent": "notification.sms.sent",
    "SmsFailed": "notification.sms.failed",
    "SendOtpSmsRequested": "identity.otp.requested",
}


class DomainEvent:
    def __init__(self, event_type: str, data: Dict[str, Any], *, source_service: str = "notification-service", version: int = 1):
        self.event_id = str(uuid.uuid4())
        self.event_type = event_type
        self.occurred_at = datetime.now(timezone.utc)
        self.version = version
        self.data = data
        self.source_service = source_service

    def to_dict(self) -> Dict[str, Any]:
        return build_event_envelope(
            self.event_type,
            self.data,
            event_version=self.version,
            source_service=self.source_service,
            routing_key=ROUTING_KEYS[self.event_type],
            event_id=self.event_id,
            occurred_at=self.occurred_at.isoformat(),
        )


class SendOtpSmsRequested(DomainEvent):
    def __init__(self, phone_number: str, code: str, purpose: str = "login", expires_in: int = 120):
        super().__init__(
            "SendOtpSmsRequested",
            {"phone_number": phone_number, "code": code, "purpose": purpose, "expires_in": expires_in},
            source_service="identity-service",
        )
