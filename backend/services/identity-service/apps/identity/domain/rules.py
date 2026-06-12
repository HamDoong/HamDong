"""Domain rules for identity-service."""

import re


class PhoneNumberRule:
    """Validates phone number format."""

    @staticmethod
    def is_valid(phone_number: str) -> bool:
        cleaned = phone_number.replace("+98", "0").replace("0098", "0").strip()
        return bool(re.match(r"^09\d{9}$", cleaned))

    @staticmethod
    def normalize(phone_number: str) -> str | None:
        cleaned = phone_number.replace("+98", "0").replace("0098", "0").strip()
        return cleaned if re.match(r"^09\d{9}$", cleaned) else None

    @staticmethod
    def mask(phone_number: str) -> str:
        normalized = PhoneNumberRule.normalize(phone_number) or ""
        if len(normalized) >= 8:
            return f"{normalized[:4]}***{normalized[-4:]}"
        return "***"


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
        return value.strip()

    @classmethod
    def is_valid(cls, value: str | None) -> bool:
        if value is None:
            return False
        return bool(cls.pattern.fullmatch(value.strip()))
