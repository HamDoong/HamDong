"""Unit tests for RequestOTPUseCase."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from src.application.dtos import OTPRequestDTO
from src.application.use_cases.request_otp import RequestOTPUseCase
from src.domain.exceptions import ValidationException, RateLimitException


@pytest.fixture
def request_otp_use_case(otp_repository, rate_limiter, otp_service, sms_service):
    """Create RequestOTPUseCase with mocked dependencies."""
    return RequestOTPUseCase(
        otp_repository=otp_repository,
        rate_limiter=rate_limiter,
        otp_service=otp_service,
        sms_service=sms_service,
    )


@pytest.mark.asyncio
class TestRequestOTPUseCase:
    """Test suite for RequestOTPUseCase."""

    async def test_execute_success(self, request_otp_use_case, sample_phone_number):
        """Test successful OTP request."""
        # Arrange
        request_dto = OTPRequestDTO(phone_number=sample_phone_number)
        client_ip = "192.168.1.1"
        
        # Mock rate limiter to allow requests
        request_otp_use_case._rate_limiter.check_rate_limit = AsyncMock()
        request_otp_use_case._rate_limiter.increment_counter = AsyncMock()
        
        # Mock SMS service
        request_otp_use_case._sms_service.send_otp_sms = AsyncMock(return_value=True)
        
        # Act
        response = await request_otp_use_case.execute(request_dto, client_ip)
        
        # Assert
        assert response.message == "OTP sent"
        assert response.expires_in == 120
        assert request_otp_use_case._rate_limiter.check_rate_limit.call_count == 2
        assert request_otp_use_case._rate_limiter.increment_counter.call_count == 2

    async def test_execute_rate_limit_exceeded_per_phone(
        self, request_otp_use_case, sample_phone_number
    ):
        """Test OTP request with per-phone rate limit exceeded."""
        # Arrange
        request_dto = OTPRequestDTO(phone_number=sample_phone_number)
        client_ip = "192.168.1.1"
        
        # Mock rate limiter to raise RateLimitException on phone check
        request_otp_use_case._rate_limiter.check_rate_limit = AsyncMock(
            side_effect=RateLimitException()
        )
        
        # Act & Assert
        with pytest.raises(RateLimitException):
            await request_otp_use_case.execute(request_dto, client_ip)

    async def test_execute_rate_limit_exceeded_per_ip(
        self, request_otp_use_case, sample_phone_number
    ):
        """Test OTP request with per-IP rate limit exceeded."""
        # Arrange
        request_dto = OTPRequestDTO(phone_number=sample_phone_number)
        client_ip = "192.168.1.1"
        
        # Mock rate limiter: first call (per phone) passes, second (per IP) fails
        request_otp_use_case._rate_limiter.check_rate_limit = AsyncMock(
            side_effect=[None, RateLimitException()]
        )
        
        # Act & Assert
        with pytest.raises(RateLimitException):
            await request_otp_use_case.execute(request_dto, client_ip)

    async def test_execute_invalid_phone_number_empty(self, request_otp_use_case):
        """Test OTP request with empty phone number."""
        # Arrange
        request_dto = OTPRequestDTO(phone_number="")
        client_ip = "192.168.1.1"
        
        # Act & Assert
        with pytest.raises(ValidationException) as exc_info:
            await request_otp_use_case.execute(request_dto, client_ip)
        
        assert exc_info.value.code == "PHONE_NUMBER_REQUIRED"

    async def test_execute_invalid_phone_number_too_short(self, request_otp_use_case):
        """Test OTP request with too short phone number."""
        # Arrange
        request_dto = OTPRequestDTO(phone_number="0912")
        client_ip = "192.168.1.1"
        
        # Act & Assert
        with pytest.raises(ValidationException) as exc_info:
            await request_otp_use_case.execute(request_dto, client_ip)
        
        assert exc_info.value.code == "INVALID_PHONE_FORMAT"

    async def test_execute_invalid_phone_number_no_leading_zero(
        self, request_otp_use_case
    ):
        """Test OTP request with phone number not starting with 0."""
        # Arrange
        request_dto = OTPRequestDTO(phone_number="19123456789")
        client_ip = "192.168.1.1"
        
        # Act & Assert
        with pytest.raises(ValidationException) as exc_info:
            await request_otp_use_case.execute(request_dto, client_ip)
        
        assert exc_info.value.code == "INVALID_PHONE_FORMAT"

    async def test_sms_sending_failure_non_blocking(
        self, request_otp_use_case, sample_phone_number
    ):
        """Test that SMS sending failure doesn't fail the request."""
        # Arrange
        request_dto = OTPRequestDTO(phone_number=sample_phone_number)
        client_ip = "192.168.1.1"
        
        # Mock rate limiter to allow requests
        request_otp_use_case._rate_limiter.check_rate_limit = AsyncMock()
        request_otp_use_case._rate_limiter.increment_counter = AsyncMock()
        
        # Mock SMS service to raise exception
        request_otp_use_case._sms_service.send_otp_sms = AsyncMock(
            side_effect=Exception("SMS service down")
        )
        
        # Act - should not raise
        response = await request_otp_use_case.execute(request_dto, client_ip)
        
        # Assert
        assert response.message == "OTP sent"
        assert response.expires_in == 120
