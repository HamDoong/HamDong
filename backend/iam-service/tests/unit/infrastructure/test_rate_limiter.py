"""Unit tests for Rate Limiter."""

import pytest
from unittest.mock import AsyncMock

from src.infrastructure.resilience.rate_limiter import RedisRateLimiter
from src.domain.exceptions import RateLimitException


@pytest.fixture
def mock_redis():
    """Create a mock Redis client."""
    redis_client = AsyncMock()
    return redis_client


class TestRedisRateLimiter:
    """Test suite for RedisRateLimiter."""

    @pytest.mark.asyncio
    async def test_check_rate_limit_within_limit(self, mock_redis):
        """Test rate limit check when within limit."""
        # Arrange
        limiter = RedisRateLimiter(mock_redis)
        mock_redis.get = AsyncMock(return_value="2")  # Current count is 2, limit is 3
        
        # Act
        result = await limiter.check_rate_limit("test_key", 3, 60)
        
        # Assert
        assert result is True

    @pytest.mark.asyncio
    async def test_check_rate_limit_exceeded(self, mock_redis):
        """Test rate limit check when limit exceeded."""
        # Arrange
        limiter = RedisRateLimiter(mock_redis)
        mock_redis.get = AsyncMock(return_value="3")  # Current count is 3, limit is 3
        
        # Act & Assert
        with pytest.raises(RateLimitException):
            await limiter.check_rate_limit("test_key", 3, 60)

    @pytest.mark.asyncio
    async def test_check_rate_limit_zero_count(self, mock_redis):
        """Test rate limit check with zero current count."""
        # Arrange
        limiter = RedisRateLimiter(mock_redis)
        mock_redis.get = AsyncMock(return_value=None)  # No counter yet
        
        # Act
        result = await limiter.check_rate_limit("test_key", 3, 60)
        
        # Assert
        assert result is True

    @pytest.mark.asyncio
    async def test_increment_counter_first_time(self, mock_redis):
        """Test counter increment on first call."""
        # Arrange
        limiter = RedisRateLimiter(mock_redis)
        mock_redis.incr = AsyncMock(return_value=1)
        mock_redis.expire = AsyncMock()
        
        # Act
        count = await limiter.increment_counter("test_key", 60)
        
        # Assert
        assert count == 1
        mock_redis.incr.assert_called_once()
        mock_redis.expire.assert_called_once()

    @pytest.mark.asyncio
    async def test_increment_counter_subsequent(self, mock_redis):
        """Test counter increment on subsequent calls."""
        # Arrange
        limiter = RedisRateLimiter(mock_redis)
        mock_redis.incr = AsyncMock(return_value=2)
        mock_redis.expire = AsyncMock()
        
        # Act
        count = await limiter.increment_counter("test_key", 60)
        
        # Assert
        assert count == 2
        mock_redis.incr.assert_called_once()
        # expire should not be called for non-first increments
        # (in this mock setup, but the actual implementation only calls on first increment)
