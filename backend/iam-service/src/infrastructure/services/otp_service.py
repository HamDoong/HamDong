"""OTP service implementation."""

import hashlib
import hmac
import os
import random
import string
from typing import Optional

from ...domain.interfaces import OTPServiceInterface


class OTPService(OTPServiceInterface):
    """OTP service for generating, hashing, and verifying OTP codes.
    
    Handles cryptographic operations for OTP codes.
    """

    # OTP configuration
    OTP_LENGTH = 6
    HASH_ALGORITHM = "sha256"

    def __init__(self, secret_key: Optional[str] = None) -> None:
        """Initialize OTP service.
        
        Args:
            secret_key: Secret key for HMAC operations. If not provided,
                       uses environment variable or generates one.
        """
        self._secret_key = (
            secret_key or os.getenv("OTP_SECRET_KEY", "default-secret-key")
        ).encode()

    def generate_otp(self) -> str:
        """Generate a new random OTP code.
        
        Returns:
            A random OTP code as a string of digits
        """
        return "".join(random.choices(string.digits, k=self.OTP_LENGTH))

    def hash_otp(self, otp: str) -> str:
        """Hash an OTP code using HMAC-SHA256.
        
        Args:
            otp: The OTP code to hash
            
        Returns:
            The hashed OTP as a hex string
        """
        otp_bytes = otp.encode()
        
        # Create HMAC-SHA256 hash
        hash_obj = hmac.new(
            self._secret_key,
            otp_bytes,
            hashlib.sha256,
        )
        
        return hash_obj.hexdigest()

    def verify_otp(self, otp: str, otp_hash: str) -> bool:
        """Verify an OTP against its hash.
        
        Uses timing-safe comparison to prevent timing attacks.
        
        Args:
            otp: The OTP code to verify
            otp_hash: The hashed OTP to verify against
            
        Returns:
            True if the OTP matches the hash, False otherwise
        """
        # Hash the provided OTP
        computed_hash = self.hash_otp(otp)
        
        # Use timing-safe comparison
        return hmac.compare_digest(computed_hash, otp_hash)
