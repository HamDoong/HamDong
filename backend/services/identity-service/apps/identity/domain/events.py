from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from apps.identity.infrastructure.event_envelope import build_event_envelope


ROUTING_KEYS = {
    "UserCreated": "identity.user.created",
    "UserUpdated": "identity.user.updated",
    "UserLoggedIn": "identity.user.logged_in",
    "SendOtpSmsRequested": "identity.otp.requested",
}


class DomainEvent:
    def __init__(self, event_type: str, data: Dict[str, Any], version: int = 1):
        self.event_id = str(uuid.uuid4())
        self.event_type = event_type
        self.occurred_at = datetime.now(timezone.utc)
        self.version = version
        self.data = data

    def to_dict(self) -> dict[str, Any]:
        return build_event_envelope(
            self.event_type,
            self.data,
            event_version=self.version,
            source_service="identity-service",
            routing_key=ROUTING_KEYS[self.event_type],
            event_id=self.event_id,
            occurred_at=self.occurred_at.isoformat(),
        )


class SendOtpSmsRequested(DomainEvent):
    def __init__(self, phone_number: str, code: str, purpose: str = "login", expires_in: int = 120):
        super().__init__(
            "SendOtpSmsRequested",
            {
                "phone_number": phone_number,
                "code": code,
                "purpose": purpose,
                "expires_in": expires_in,
            },
        )


class UserCreated(DomainEvent):
    def __init__(
        self,
        user_id: str,
        phone_number: str,
        display_name: str = None,
        art_name: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        role: str = "USER",
        is_active: bool = True,
    ):
        super().__init__(
            "UserCreated",
            {
                "user_id": str(user_id),
                "phone_number": phone_number,
                "display_name": display_name,
                "art_name": art_name,
                "first_name": first_name,
                "last_name": last_name,
                "role": role,
                "is_active": is_active,
            },
        )


class UserUpdated(DomainEvent):
    def __init__(
        self,
        user_id: str,
        phone_number: str,
        display_name: str = None,
        art_name: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        role: str = "USER",
        is_active: bool = True,
    ):
        super().__init__(
            "UserUpdated",
            {
                "user_id": str(user_id),
                "phone_number": phone_number,
                "display_name": display_name,
                "art_name": art_name,
                "first_name": first_name,
                "last_name": last_name,
                "role": role,
                "is_active": is_active,
            },
        )


class UserLoggedIn(DomainEvent):
    def __init__(self, user_id: str, phone_number: str):
        super().__init__(
            "UserLoggedIn",
            {
                "user_id": str(user_id),
                "phone_number": phone_number,
            },
        )
