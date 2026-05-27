"""UseCase for requesting OTP.

This use case handles the business logic for OTP request:
1. Validate phone number format
2. Check rate limits (per phone and per IP)
3. Generate OTP
4. Hash and store OTP in Redis
5. Publish SMS sending event
6. Return response
"""

from datetime import datetime, timedelta
from typing import Tuple

from ..dtos import OTPRequestDTO, OTPResponseDTO
from ...domain.entities import OTPEntity
from ...domain.exceptions import RateLimitException, ValidationException
from ...domain.interfaces import (
    OTPRepositoryInterface,
    OTPServiceInterface,
    RateLimiterInterface,
    SMSServiceInterface,
)


class RequestOTPUseCase:
    """UseCase for requesting OTP.
    
    Orchestrates the OTP request business logic including validation,
    rate limiting, generation, storage, and SMS sending.
    """

    # Rate limiting constants
    OTP_REQUESTS_PER_PHONE = 3
    OTP_REQUESTS_WINDOW_PHONE = 5 * 60  # 5 minutes
    OTP_REQUESTS_PER_IP = 10
    OTP_REQUESTS_WINDOW_IP = 60  # 1 minute
    
    # OTP configuration
    OTP_TTL_SECONDS = 120

    def __init__(
        self,
        otp_repository: OTPRepositoryInterface,
        rate_limiter: RateLimiterInterface,
        otp_service: OTPServiceInterface,
        sms_service: SMSServiceInterface,
    ) -> None:
        """Initialize the RequestOTPUseCase.
        
        Args:
            otp_repository: Repository for OTP storage
            rate_limiter: Rate limiter for checking limits
            otp_service: Service for OTP generation and hashing
            sms_service: Service for sending SMS
        """
        self._otp_repository = otp_repository
        self._rate_limiter = rate_limiter
        self._otp_service = otp_service
        self._sms_service = sms_service

    async def execute(
        self, request: OTPRequestDTO, client_ip: str
    ) -> OTPResponseDTO:
        """Execute the OTP request use case.
        
        Args:
            request: The OTP request DTO containing phone number
            client_ip: The client's IP address for rate limiting
            
        Returns:
            OTPResponseDTO with success message and expiration time
            
        Raises:
            ValidationException: If phone number is invalid
            RateLimitException: If rate limits are exceeded
        """
        phone_number = request.phone_number
        
        # Step 1: Validate phone number format
        self._validate_phone_number(phone_number)
        
        # Step 2: Check rate limits
        await self._check_rate_limits(phone_number, client_ip)
        
        # Step 3: Generate OTP
        otp_code = self._otp_service.generate_otp()
        otp_hash = self._otp_service.hash_otp(otp_code)
        
        # Step 4: Create and store OTP entity
        expires_at = datetime.utcnow() + timedelta(seconds=self.OTP_TTL_SECONDS)
        otp_entity = OTPEntity(
            phone_number=phone_number,
            otp_hash=otp_hash,
            expires_at=expires_at,
            attempts=0,
        )
        await self._otp_repository.save(otp_entity)
        
        # Step 5: Send SMS (asynchronously, non-blocking)
        # In production, this would be published to a message queue
        try:
            await self._sms_service.send_otp_sms(phone_number, otp_code)
        except Exception as e:
            # Log the error but don't fail the request
            # SMS sending should be resilient with retries
            print(f"Failed to send OTP SMS to {phone_number}: {str(e)}")
        
        # Step 6: Return success response
        return OTPResponseDTO(
            message="OTP sent",
            expires_in=self.OTP_TTL_SECONDS,
        )

    async def _check_rate_limits(self, phone_number: str, client_ip: str) -> None:
        """Check rate limits for phone number and IP.
        
        Args:
            phone_number: The phone number to check
            client_ip: The client IP address to check
            
        Raises:
            RateLimitException: If any rate limit is exceeded
        """
        # Check per-phone rate limit
        phone_key = f"otp:request:phone:{phone_number}"
        await self._rate_limiter.check_rate_limit(
            phone_key,
            self.OTP_REQUESTS_PER_PHONE,
            self.OTP_REQUESTS_WINDOW_PHONE,
        )
        
        # Check per-IP rate limit
        ip_key = f"otp:request:ip:{client_ip}"
        await self._rate_limiter.check_rate_limit(
            ip_key,
            self.OTP_REQUESTS_PER_IP,
            self.OTP_REQUESTS_WINDOW_IP,
        )
        
        # Increment counters after checks pass
        await self._rate_limiter.increment_counter(
            phone_key, self.OTP_REQUESTS_WINDOW_PHONE
        )
        await self._rate_limiter.increment_counter(
            ip_key, self.OTP_REQUESTS_WINDOW_IP
        )

    def _validate_phone_number(self, phone_number: str) -> None:
        """Validate phone number format.
        
        Args:
            phone_number: The phone number to validate
            
        Raises:
            ValidationException: If phone number format is invalid
        """
        if not phone_number:
            raise ValidationException(
                "Phone number is required",
                "PHONE_NUMBER_REQUIRED",
            )
        
        if len(phone_number) < 10 or len(phone_number) > 15:
            raise ValidationException(
                "Phone number must be between 10 and 15 digits",
                "INVALID_PHONE_FORMAT",
            )
        
        if not phone_number[0] == "0" or not phone_number.isdigit():
            raise ValidationException(
                "Phone number must start with 0 and contain only digits",
                "INVALID_PHONE_FORMAT",
            )
