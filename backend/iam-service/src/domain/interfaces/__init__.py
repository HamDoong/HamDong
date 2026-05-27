"""Domain interfaces module."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

from ..entities import OTPEntity


class OTPRepositoryInterface(ABC):
    """Interface for OTP repository operations.
    
    Defines the contract for OTP storage operations.
    """

    @abstractmethod
    async def save(self, otp: OTPEntity) -> None:
        """Save an OTP entity.
        
        Args:
            otp: The OTP entity to save
        """
        pass

    @abstractmethod
    async def get_by_phone(self, phone_number: str) -> Optional[OTPEntity]:
        """Retrieve OTP by phone number.
        
        Args:
            phone_number: The phone number to look up
            
        Returns:
            The OTP entity if found, None otherwise
        """
        pass

    @abstractmethod
    async def delete_by_phone(self, phone_number: str) -> None:
        """Delete OTP for a phone number.
        
        Args:
            phone_number: The phone number to delete OTP for
        """
        pass


class RateLimiterInterface(ABC):
    """Interface for rate limiting operations.
    
    Defines the contract for rate limiting checks.
    """

    @abstractmethod
    async def check_rate_limit(
        self, key: str, limit: int, window_seconds: int
    ) -> bool:
        """Check if a rate limit has been exceeded.
        
        Args:
            key: The rate limit key (e.g., phone number, IP address)
            limit: The maximum number of requests allowed
            window_seconds: The time window in seconds
            
        Returns:
            True if within limit, False if exceeded
            
        Raises:
            RateLimitException: If rate limit is exceeded
        """
        pass

    @abstractmethod
    async def increment_counter(self, key: str, window_seconds: int) -> int:
        """Increment a counter for rate limiting.
        
        Args:
            key: The rate limit key
            window_seconds: The time window in seconds
            
        Returns:
            The new counter value
        """
        pass


class OTPServiceInterface(ABC):
    """Interface for OTP service operations.
    
    Defines the contract for OTP generation and hashing.
    """

    @abstractmethod
    def generate_otp(self) -> str:
        """Generate a new OTP code.
        
        Returns:
            A new OTP code as a string
        """
        pass

    @abstractmethod
    def hash_otp(self, otp: str) -> str:
        """Hash an OTP code.
        
        Args:
            otp: The OTP code to hash
            
        Returns:
            The hashed OTP
        """
        pass

    @abstractmethod
    def verify_otp(self, otp: str, otp_hash: str) -> bool:
        """Verify an OTP against its hash.
        
        Args:
            otp: The OTP code to verify
            otp_hash: The hashed OTP to verify against
            
        Returns:
            True if the OTP matches the hash, False otherwise
        """
        pass


class SMSServiceInterface(ABC):
    """Interface for SMS service operations.
    
    Defines the contract for sending SMS messages.
    """

    @abstractmethod
    async def send_otp_sms(self, phone_number: str, otp: str) -> bool:
        """Send OTP via SMS.
        
        Args:
            phone_number: The recipient's phone number
            otp: The OTP code to send
            
        Returns:
            True if SMS was sent successfully, False otherwise
            
        Raises:
            Exception: If SMS sending fails critically
        """
        pass
