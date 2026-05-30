"""Domain rules for notification-service."""

import re
from typing import Optional


class PhoneNumberRule:
    """Validate and mask Iranian mobile numbers."""

    @staticmethod
    def normalize(phone_number: str) -> Optional[str]:
        if not isinstance(phone_number, str):
            return None

        cleaned = phone_number.strip().replace("+98", "0").replace("0098", "0")
        cleaned = re.sub(r"\D", "", cleaned)

        if cleaned.startswith("98") and len(cleaned) == 12:
            cleaned = f"0{cleaned[2:]}"

        if cleaned.startswith("9") and len(cleaned) == 10:
            cleaned = f"0{cleaned}"

        return cleaned if re.match(r"^09\d{9}$", cleaned) else None

    @staticmethod
    def is_valid(phone_number: str) -> bool:
        return PhoneNumberRule.normalize(phone_number) is not None

    @staticmethod
    def mask(phone_number: str) -> str:
        normalized = PhoneNumberRule.normalize(phone_number) or ""
        if len(normalized) >= 8:
            return f"{normalized[:4]}***{normalized[-4:]}"
        return "***"


def sanitize_message_text(message: str) -> str:
    """Remove obvious OTP-like sequences from stored logs."""
    if not message:
        return ""
    return re.sub(r"\b\d{4,8}\b", "******", message)
