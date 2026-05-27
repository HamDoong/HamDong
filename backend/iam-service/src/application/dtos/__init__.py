"""Data Transfer Objects for authentication operations."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, validator


class OTPRequestDTO(BaseModel):
    """DTO for OTP request.
    
    Used to receive OTP request from the API.
    """

    phone_number: str = Field(..., min_length=10, max_length=15)

    @validator("phone_number")
    def validate_phone_number(cls, v: str) -> str:
        """Validate phone number format.
        
        Args:
            v: The phone number to validate
            
        Returns:
            The validated phone number
            
        Raises:
            ValueError: If phone number format is invalid
        """
        if not v.startswith("0") or not v.isdigit():
            raise ValueError("Phone number must start with 0 and contain only digits")
        return v

    class Config:
        """Pydantic config."""

        schema_extra = {
            "example": {"phone_number": "09123456789"},
        }


class OTPResponseDTO(BaseModel):
    """DTO for OTP response.
    
    Used to return the API response after OTP request.
    """

    message: str
    expires_in: int

    class Config:
        """Pydantic config."""

        schema_extra = {
            "example": {"message": "OTP sent", "expires_in": 120},
        }


class OTPVerificationDTO(BaseModel):
    """DTO for OTP verification.
    
    Used to verify the OTP provided by user.
    """

    phone_number: str = Field(..., min_length=10, max_length=15)
    otp: str = Field(..., min_length=4, max_length=6)

    class Config:
        """Pydantic config."""

        schema_extra = {
            "example": {"phone_number": "09123456789", "otp": "123456"},
        }


class OTPInternalDTO(BaseModel):
    """Internal DTO for OTP entity.
    
    Used internally to transfer OTP data between layers.
    """

    phone_number: str
    otp_hash: str
    expires_at: datetime
    attempts: int = 0
