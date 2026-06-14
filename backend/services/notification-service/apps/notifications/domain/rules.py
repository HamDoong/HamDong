"""Domain rules for notification-service."""

from __future__ import annotations

import re
from typing import Optional

from django.core.exceptions import ValidationError
from django.core.validators import validate_email


class EmailRule:
    """Validate and mask email addresses."""

    @staticmethod
    def normalize(email: str) -> Optional[str]:
        if not isinstance(email, str):
            return None
        cleaned = email.strip().lower()
        if not cleaned:
            return None
        try:
            validate_email(cleaned)
        except ValidationError:
            return None
        return cleaned

    @staticmethod
    def is_valid(email: str) -> bool:
        return EmailRule.normalize(email) is not None

    @staticmethod
    def mask(email: str) -> str:
        normalized = EmailRule.normalize(email) or ""
        if not normalized or "@" not in normalized:
            return "***"
        local_part, domain = normalized.split("@", 1)
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


def sanitize_message_text(message: str) -> str:
    """Remove obvious OTP-like sequences from stored logs."""
    if not message:
        return ""
    return re.sub(r"\b\d{4,8}\b", "******", message)
