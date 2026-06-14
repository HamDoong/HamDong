from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AuthenticatedUser:
    id: str
    email: str | None
    role: str
    token_jti: str

    @property
    def sub(self) -> str:
        return self.id

    @property
    def jti(self) -> str:
        return self.token_jti

    @property
    def identity_user_id(self) -> str:
        return self.id

    @property
    def username(self) -> str:
        return self.email or self.id

    @property
    def is_authenticated(self) -> bool:
        return True

    @property
    def is_anonymous(self) -> bool:
        return False
