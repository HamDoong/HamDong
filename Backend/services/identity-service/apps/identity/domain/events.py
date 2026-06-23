from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from apps.identity.infrastructure.event_envelope import build_event_envelope


ROUTING_KEYS = {
    "UserCreated": "identity.user.created",
    "UserUpdated": "identity.user.updated",
    "UserLoggedIn": "identity.user.logged_in",
    "SendOtpEmailRequested": "identity.otp.requested",
    "PasswordChanged": "identity.user.password_changed",
    "UserBankCardCreated": "identity.user_bank_card.created",
    "UserBankCardUpdated": "identity.user_bank_card.updated",
    "UserBankCardDeactivated": "identity.user_bank_card.deactivated",
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


class SendOtpEmailRequested(DomainEvent):
    def __init__(self, email: str, code: str, purpose: str = "login", expires_in: int = 120):
        super().__init__(
            "SendOtpEmailRequested",
            {
                "email": email,
                "code": code,
                "purpose": purpose,
                "expires_in": expires_in,
            },
        )


class UserCreated(DomainEvent):
    def __init__(
        self,
        user_id: str,
        email: str,
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
                "email": email,
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
        email: str,
        art_name: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        display_name: str | None = None,
        avatar_url: str | None = None,
        role: str = "USER",
        is_active: bool = True,
    ):
        super().__init__(
            "UserUpdated",
            {
                "user_id": str(user_id),
                "email": email,
                "art_name": art_name,
                "first_name": first_name,
                "last_name": last_name,
                "display_name": display_name,
                "avatar_url": avatar_url,
                "role": role,
                "is_active": is_active,
            },
        )


class UserLoggedIn(DomainEvent):
    def __init__(self, user_id: str, email: str):
        super().__init__(
            "UserLoggedIn",
            {
                "user_id": str(user_id),
                "email": email,
            },
        )


class PasswordChanged(DomainEvent):
    def __init__(self, user_id: str, changed_at: str, other_sessions_revoked: bool):
        super().__init__(
            "PasswordChanged",
            {
                "user_id": str(user_id),
                "changed_at": changed_at,
                "other_sessions_revoked": other_sessions_revoked,
            },
        )


class UserBankCardCreated(DomainEvent):
    def __init__(
        self,
        *,
        card_id: str,
        user_id: str,
        holder_name: str,
        bank_name: str | None,
        card_number_last4: str,
        masked_card_number: str,
        is_default: bool,
        is_active: bool,
        updated_at,
    ):
        super().__init__(
            "UserBankCardCreated",
            {
                "card_id": str(card_id),
                "user_id": str(user_id),
                "holder_name": holder_name,
                "bank_name": bank_name,
                "card_number_last4": card_number_last4,
                "masked_card_number": masked_card_number,
                "is_default": is_default,
                "is_active": is_active,
                "updated_at": updated_at.isoformat() if hasattr(updated_at, "isoformat") else updated_at,
            },
        )


class UserBankCardUpdated(UserBankCardCreated):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.event_type = "UserBankCardUpdated"


class UserBankCardDeactivated(UserBankCardCreated):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.event_type = "UserBankCardDeactivated"
