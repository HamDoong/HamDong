"""Domain rules for identity-service."""

import re


class PhoneNumberRule:
    """Validates phone number format."""

    @staticmethod
    def is_valid(phone_number: str) -> bool:
        """
        Validate Iranian phone number format.
        Accepts formats like: 09123456789, +989123456789, 00989123456789
        """
        # Remove common prefixes
        cleaned = phone_number.replace("+98", "0").replace("0098", "0").strip()

        # Check if it starts with 09 and has 11 digits
        return bool(re.match(r"^09\d{9}$", cleaned))

    @staticmethod
    def normalize(phone_number: str) -> str:
        """Normalize phone number to 09XXXXXXXXX format."""
        cleaned = phone_number.replace("+98", "0").replace("0098", "0").strip()
        return cleaned if re.match(r"^09\d{9}$", cleaned) else None


class OtpRule:
    """Rules for OTP generation and verification."""

    @staticmethod
    def is_valid_length(code: str, length: int = 6) -> bool:
        """Check if OTP code has valid length and is numeric."""
        return len(code) == length and code.isdigit()
