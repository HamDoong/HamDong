"""Integration tests for Redis OTP Repository."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

from src.domain.entities import OTPEntity
from src.infrastructure.redis.otp_repository import RedisOTPRepository


@pytest.fixture
def mock_redis():
    """Create a mock Redis client."""
    redis_client = AsyncMock()
    return redis_client


class TestRedisOTPRepository:
    """Test suite for RedisOTPRepository."""

    @pytest.mark.asyncio
    async def test_save_otp(self, mock_redis):
        """Test saving OTP to Redis."""
        # Arrange
        repo = RedisOTPRepository(mock_redis)
        expires_at = datetime.utcnow() + timedelta(seconds=120)
        otp = OTPEntity(
            phone_number="09123456789",
            otp_hash="hashed_value",
            expires_at=expires_at,
            attempts=0,
        )
        
        mock_redis.setex = AsyncMock()
        
        # Act
        await repo.save(otp)
        
        # Assert
        assert mock_redis.setex.called
        call_args = mock_redis.setex.call_args
        assert call_args[0][0] == "otp:09123456789"

    @pytest.mark.asyncio
    async def test_get_otp_by_phone_exists(self, mock_redis):
        """Test retrieving existing OTP."""
        # Arrange
        repo = RedisOTPRepository(mock_redis)
        expires_at = datetime.utcnow() + timedelta(seconds=120)
        
        import json
        otp_data = {
            "phone_number": "09123456789",
            "otp_hash": "hashed_value",
            "expires_at": expires_at.isoformat(),
            "attempts": 0,
        }
        
        mock_redis.get = AsyncMock(return_value=json.dumps(otp_data))
        
        # Act
        result = await repo.get_by_phone("09123456789")
        
        # Assert
        assert result is not None
        assert result.phone_number == "09123456789"
        assert result.otp_hash == "hashed_value"

    @pytest.mark.asyncio
    async def test_get_otp_by_phone_not_exists(self, mock_redis):
        """Test retrieving non-existent OTP."""
        # Arrange
        repo = RedisOTPRepository(mock_redis)
        mock_redis.get = AsyncMock(return_value=None)
        
        # Act
        result = await repo.get_by_phone("09123456789")
        
        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_otp_by_phone(self, mock_redis):
        """Test deleting OTP by phone number."""
        # Arrange
        repo = RedisOTPRepository(mock_redis)
        mock_redis.delete = AsyncMock()
        
        # Act
        await repo.delete_by_phone("09123456789")
        
        # Assert
        mock_redis.delete.assert_called_once_with("otp:09123456789")
