"""Domain rules for identity-service."""

from __future__ import annotations

import re

from django.core.exceptions import ValidationError
from django.core.validators import validate_email


class EmailRule:
    """Validate, normalize, and mask email addresses."""

    @staticmethod
    def normalize(email: str | None) -> str | None:
        if not isinstance(email, str):
            return None
        normalized = email.strip().lower()
        if not normalized:
            return None
        try:
            validate_email(normalized)
        except ValidationError:
            return None
        return normalized

    @staticmethod
    def is_valid(email: str | None) -> bool:
        return EmailRule.normalize(email) is not None

    @staticmethod
    def mask(email: str | None) -> str:
        normalized = EmailRule.normalize(email)
        if not normalized:
            return "***"
        local_part, _, domain = normalized.partition("@")
        if len(local_part) <= 2:
            masked_local = local_part[:1] + "***"
        else:
            masked_local = local_part[:2] + "***"
        if "." in domain:
            domain_name, dot, suffix = domain.partition(".")
            masked_domain = (domain_name[:1] + "***" if domain_name else "***") + dot + suffix
        else:
            masked_domain = domain[:1] + "***"
        return f"{masked_local}@{masked_domain}"


class OtpRule:
    """Rules for OTP generation and verification."""

    @staticmethod
    def is_valid_length(code: str, length: int = 6) -> bool:
        return len(code) == length and code.isdigit()


class ArtNameRule:
    pattern = re.compile(r"^[\w\-\u0600-\u06FF]{3,32}$", re.UNICODE)

    @classmethod
    def normalize(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @classmethod
    def sanitize_candidate(cls, value: str | None) -> str | None:
        normalized = cls.normalize(value)
        if normalized is None:
            return None
        normalized = re.sub(r"\s+", "-", normalized)
        normalized = re.sub(r"[^\w\-\u0600-\u06FF]", "-", normalized, flags=re.UNICODE)
        normalized = re.sub(r"-{2,}", "-", normalized).strip("-_")
        return normalized[:32] or None

    @classmethod
    def is_valid(cls, value: str | None) -> bool:
        if value is None:
            return False
        return bool(cls.pattern.fullmatch(value.strip()))
