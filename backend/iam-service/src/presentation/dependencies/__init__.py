"""FastAPI endpoint dependencies using dependency injection."""

from typing import Annotated, AsyncGenerator

import redis.asyncio as redis
from fastapi import Depends

from src.application.use_cases.request_otp import RequestOTPUseCase
from src.infrastructure.resilience.rate_limiter import RedisRateLimiter
from src.infrastructure.redis.otp_repository import RedisOTPRepository
from src.infrastructure.services.otp_service import OTPService
from src.infrastructure.services.sms_service import MockSMSService
from src.configuration.settings import get_settings


# Singleton instances (in production, use a DI container)
_redis_client: redis.Redis | None = None


async def get_redis_client() -> AsyncGenerator[redis.Redis, None]:
    """Get Redis client instance.
    
    Yields:
        The Redis async client
    """
    global _redis_client
    
    settings = get_settings()
    
    if _redis_client is None:
        _redis_client = await redis.from_url(
            settings.redis_url,
            encoding="utf8",
            decode_responses=True,
        )
    
    try:
        yield _redis_client
    finally:
        pass


async def get_otp_use_case(
    redis_client: Annotated[redis.Redis, Depends(get_redis_client)],
) -> RequestOTPUseCase:
    """Get RequestOTPUseCase instance with dependencies injected.
    
    Args:
        redis_client: The Redis client instance
        
    Returns:
        RequestOTPUseCase instance
    """
    # Initialize repositories and services
    otp_repository = RedisOTPRepository(redis_client)
    rate_limiter = RedisRateLimiter(redis_client)
    otp_service = OTPService()
    sms_service = MockSMSService()  # Use MockSMSService for development
    
    # Create and return the use case
    return RequestOTPUseCase(
        otp_repository=otp_repository,
        rate_limiter=rate_limiter,
        otp_service=otp_service,
        sms_service=sms_service,
    )
