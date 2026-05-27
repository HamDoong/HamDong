"""Pytest configuration and fixtures."""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
import redis.asyncio as redis

from src.domain.entities import OTPEntity
from src.domain.interfaces import (
    OTPRepositoryInterface,
    RateLimiterInterface,
    OTPServiceInterface,
    SMSServiceInterface,
)
from src.infrastructure.redis.otp_repository import RedisOTPRepository
from src.infrastructure.resilience.rate_limiter import RedisRateLimiter
from src.infrastructure.services.otp_service import OTPService
from src.infrastructure.services.sms_service import MockSMSService


@pytest.fixture
def mock_redis_client():
    """Create a mock Redis client."""
    client = AsyncMock(spec=redis.Redis)
    return client


@pytest.fixture
def otp_service():
    """Create an OTP service instance."""
    return OTPService(secret_key="test-secret-key")


@pytest.fixture
def sms_service():
    """Create an SMS service instance."""
    return MockSMSService()


@pytest.fixture
def otp_repository(mock_redis_client):
    """Create an OTP repository instance with mock Redis."""
    return RedisOTPRepository(mock_redis_client)


@pytest.fixture
def rate_limiter(mock_redis_client):
    """Create a rate limiter instance with mock Redis."""
    return RedisRateLimiter(mock_redis_client)


@pytest.fixture
def sample_phone_number():
    """Sample valid phone number."""
    return "09123456789"


@pytest.fixture
def sample_otp_code():
    """Sample OTP code."""
    return "123456"
