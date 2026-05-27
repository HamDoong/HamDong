"""Domain entities module."""

from datetime import datetime
from typing import Optional


class OTPEntity:
    """Domain entity representing an OTP record.
    
    This entity represents a one-time password that has been generated
    and stored for a user authentication request.
    """

    def __init__(
        self,
        phone_number: str,
        otp_hash: str,
        expires_at: datetime,
        attempts: int = 0,
    ) -> None:
        """Initialize OTP entity.
        
        Args:
            phone_number: The phone number the OTP was sent to
            otp_hash: The hashed OTP value
            expires_at: When the OTP expires
            attempts: Number of verification attempts made
        """
        self.phone_number = phone_number
        self.otp_hash = otp_hash
        self.expires_at = expires_at
        self.attempts = attempts

    def is_expired(self) -> bool:
        """Check if OTP has expired.
        
        Returns:
            True if OTP has expired, False otherwise
        """
        return datetime.utcnow() > self.expires_at

    def increment_attempts(self) -> None:
        """Increment verification attempt counter."""
        self.attempts += 1


class UserEntity:
    """Domain entity representing a user.
    
    This is a simplified user entity for the authentication context.
    """

    def __init__(
        self,
        user_id: str,
        phone_number: str,
        verified: bool = False,
    ) -> None:
        """Initialize user entity.
        
        Args:
            user_id: Unique user identifier
            phone_number: User's phone number
            verified: Whether the user's phone is verified
        """
        self.user_id = user_id
        self.phone_number = phone_number
        self.verified = verified
