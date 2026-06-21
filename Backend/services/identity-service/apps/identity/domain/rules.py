"""Domain rules for identity-service."""

from __future__ import annotations

import re
import unicodedata
from datetime import date

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import validate_email


_PERSIAN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
_ALLOWED_NAME_PUNCTUATION = {"'", "-", ".", "(", ")"}
_ALLOWED_BIO_CONTROLS = {"\n", "\r", "\t"}
_ALLOWED_PROFILE_FORMAT_CHARS = {"\u200c"}

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


class ProfileRule:
    """Shared normalization and validation for profile text fields."""

    @staticmethod
    def _normalize_whitespace(value: str) -> str:
        return re.sub(r"\s+", " ", value).strip()

    @staticmethod
    def _contains_disallowed_controls(value: str, *, allow_newlines: bool = False) -> bool:
        allowed_controls = _ALLOWED_BIO_CONTROLS if allow_newlines else set()
        for character in value:
            if character == "\x00":
                return True
            if character in _ALLOWED_PROFILE_FORMAT_CHARS:
                continue
            if unicodedata.category(character).startswith("C") and character not in allowed_controls:
                return True
        return False

    @classmethod
    def normalize_optional_text(
        cls,
        value: str | None,
        *,
        max_length: int,
        min_length: int = 0,
        allow_newlines: bool = False,
        field_name: str = "value",
    ) -> str | None:
        if value is None:
            return None
        if isinstance(value, bool) or not isinstance(value, str):
            raise ValueError(f"INVALID_{field_name.upper()}")
        normalized = value.strip()
        if allow_newlines:
            normalized = re.sub(r"[\t\x0b\x0c\r ]+", " ", normalized)
            normalized = re.sub(r"\n{3,}", "\n\n", normalized).strip()
        else:
            normalized = cls._normalize_whitespace(value)
        if not normalized:
            return None
        if cls._contains_disallowed_controls(normalized, allow_newlines=allow_newlines):
            raise ValueError(f"INVALID_{field_name.upper()}")
        if len(normalized) < min_length:
            raise ValueError(f"INVALID_{field_name.upper()}")
        if len(normalized) > max_length:
            raise ValueError(f"INVALID_{field_name.upper()}")
        return normalized

    @classmethod
    def normalize_display_name(cls, value: str | None) -> str | None:
        normalized = cls.normalize_optional_text(
            value,
            max_length=int(getattr(settings, "PROFILE_DISPLAY_NAME_MAX_LENGTH", 150)),
            min_length=int(getattr(settings, "PROFILE_DISPLAY_NAME_MIN_LENGTH", 2)),
            field_name="display_name",
        )
        if normalized is None:
            return None
        for character in normalized:
            if unicodedata.category(character).startswith(("L", "M")) or character.isspace():
                continue
            if character in _ALLOWED_NAME_PUNCTUATION:
                continue
            raise ValueError("INVALID_DISPLAY_NAME")
        return normalized

    @classmethod
    def normalize_city(cls, value: str | None) -> str | None:
        return cls.normalize_optional_text(
            value,
            max_length=int(getattr(settings, "PROFILE_CITY_MAX_LENGTH", 150)),
            field_name="city",
        )

    @classmethod
    def normalize_bio(cls, value: str | None) -> str | None:
        return cls.normalize_optional_text(
            value,
            max_length=int(getattr(settings, "PROFILE_BIO_MAX_LENGTH", 500)),
            allow_newlines=True,
            field_name="bio",
        )


class PhoneNumberRule:
    """Normalize supported Iranian mobile numbers to +98 canonical form."""

    @staticmethod
    def _normalize_digits(value: str) -> str:
        return value.translate(_PERSIAN_DIGITS)

    @classmethod
    def normalize(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if isinstance(value, bool) or not isinstance(value, str):
            raise ValueError("INVALID_PHONE_NUMBER")
        normalized = cls._normalize_digits(value.strip())
        if not normalized:
            return None
        if re.search(r"[A-Za-z]", normalized):
            raise ValueError("INVALID_PHONE_NUMBER")
        normalized = re.sub(r"[\s\-()]+", "", normalized)
        if not normalized:
            return None
        if normalized.startswith("0098"):
            normalized = "+" + normalized[2:]
        elif normalized.startswith("98"):
            normalized = "+" + normalized
        elif normalized.startswith("09"):
            normalized = "+98" + normalized[1:]
        if not re.fullmatch(r"\+989\d{9}", normalized):
            raise ValueError("INVALID_PHONE_NUMBER")
        return normalized


class DateOfBirthRule:
    """Validation helpers for date-of-birth."""

    @staticmethod
    def validate(value: date | None) -> date | None:
        if value is None:
            return None
        today = date.today()
        max_age_years = int(getattr(settings, "PROFILE_MAX_AGE_YEARS", 120))
        try:
            earliest = date(today.year - max_age_years, today.month, today.day)
        except ValueError:
            earliest = date(today.year - max_age_years, today.month, today.day - 1)
        if value > today or value < earliest:
            raise ValueError("INVALID_DATE_OF_BIRTH")
        return value
