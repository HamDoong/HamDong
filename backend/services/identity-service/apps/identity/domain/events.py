import uuid
from datetime import datetime, timezone
from typing import Any, Dict


class DomainEvent:
    """Base class for domain events."""

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

    def to_dict(self):
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "occurred_at": self.occurred_at.isoformat(),
            "version": self.version,
            "data": self.data,
        }


class UserOtpRequested(DomainEvent):
    """Event published when OTP is requested."""

    def __init__(self, phone_number: str, purpose: str = "login"):
        super().__init__(
            event_id=str(uuid.uuid4()),
            event_type="UserOtpRequested",
            occurred_at=datetime.utcnow(),
            version=1,
            data={"phone_number": phone_number, "purpose": purpose},
        )


class SendOtpSmsRequested(DomainEvent):
    """Command event published for notification-service to send OTP SMS."""

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


class UserCreated(DomainEvent):
    """Event published when a new user is created."""

    def __init__(
        self,
        user_id: str,
        phone_number: str,
        display_name: str = None,
        role: str = "USER",
        is_active: bool = True,
    ):
        super().__init__(
            event_id=str(uuid.uuid4()),
            event_type="UserCreated",
            occurred_at=datetime.utcnow(),
            version=1,
            data={
                "user_id": str(user_id),
                "phone_number": phone_number,
                "display_name": display_name,
                "role": role,
                "is_active": is_active,
            },
        )


class UserUpdated(DomainEvent):
    """Event published when a user is updated."""

    def __init__(
        self,
        user_id: str,
        phone_number: str,
        display_name: str = None,
        role: str = "USER",
        is_active: bool = True,
    ):
        super().__init__(
            event_id=str(uuid.uuid4()),
            event_type="UserUpdated",
            occurred_at=datetime.utcnow(),
            version=1,
            data={
                "user_id": str(user_id),
                "phone_number": phone_number,
                "display_name": display_name,
                "role": role,
                "is_active": is_active,
            },
        )


class UserLoggedIn(DomainEvent):
    """Event published when a user logs in."""

    def __init__(self, user_id: str, phone_number: str):
        super().__init__(
            event_id=str(uuid.uuid4()),
            event_type="UserLoggedIn",
            occurred_at=datetime.utcnow(),
            version=1,
            data={"user_id": str(user_id), "phone_number": phone_number},
        )
