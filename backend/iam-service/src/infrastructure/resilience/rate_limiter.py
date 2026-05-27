"""Rate limiter implementation using Redis."""

import redis.asyncio as redis

from ...domain.exceptions import RateLimitException
from ...domain.interfaces import RateLimiterInterface


class RedisRateLimiter(RateLimiterInterface):
    """Redis-based rate limiter using sliding window counter.
    
    Implements rate limiting with Redis for distributed systems.
    """

    def __init__(self, redis_client: redis.Redis) -> None:
        """Initialize Redis rate limiter.
        
        Args:
            redis_client: The Redis async client instance
        """
        self._redis = redis_client

    def _get_counter_key(self, key: str) -> str:
        """Get the Redis key for a rate limit counter.
        
        Args:
            key: The rate limit key
            
        Returns:
            The Redis counter key
        """
        return f"rate_limit:{key}"

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
        counter_key = self._get_counter_key(key)
        
        # Get current counter value
        current_count = await self._redis.get(counter_key)
        current_count = int(current_count) if current_count else 0
        
        if current_count >= limit:
            raise RateLimitException(
                f"Rate limit exceeded for key: {key}",
                "RATE_LIMIT_EXCEEDED",
            )
        
        return True

    async def increment_counter(self, key: str, window_seconds: int) -> int:
        """Increment a counter for rate limiting.
        
        Args:
            key: The rate limit key
            window_seconds: The time window in seconds
            
        Returns:
            The new counter value
        """
        counter_key = self._get_counter_key(key)
        
        # Increment the counter
        new_count = await self._redis.incr(counter_key)
        
        # Set expiration on first increment
        if new_count == 1:
            await self._redis.expire(counter_key, window_seconds)
        
        return new_count
