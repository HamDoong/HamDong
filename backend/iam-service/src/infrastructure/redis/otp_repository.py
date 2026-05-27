"""Redis-based OTP repository implementation."""

import json
from typing import Optional

import redis.asyncio as redis

from ...domain.entities import OTPEntity
from ...domain.interfaces import OTPRepositoryInterface


class RedisOTPRepository(OTPRepositoryInterface):
    """Redis implementation of OTP repository.
    
    Stores OTP data in Redis with configurable TTL for security.
    """

    def __init__(self, redis_client: redis.Redis) -> None:
        """Initialize Redis OTP repository.
        
        Args:
            redis_client: The Redis async client instance
        """
        self._redis = redis_client

    def _get_key(self, phone_number: str) -> str:
        """Get the Redis key for an OTP.
        
        Args:
            phone_number: The phone number
            
        Returns:
            The Redis key
        """
        return f"otp:{phone_number}"

    async def save(self, otp: OTPEntity) -> None:
        """Save an OTP entity to Redis.
        
        Args:
            otp: The OTP entity to save
        """
        key = self._get_key(otp.phone_number)
        
        # Prepare data for storage
        data = {
            "phone_number": otp.phone_number,
            "otp_hash": otp.otp_hash,
            "expires_at": otp.expires_at.isoformat(),
            "attempts": otp.attempts,
        }
        
        # Calculate TTL (time to expiration)
        ttl = int((otp.expires_at - otp.expires_at.now()).total_seconds())
        ttl = max(ttl, 120)  # Ensure minimum TTL of 120 seconds
        
        # Store in Redis with expiration
        await self._redis.setex(
            key,
            ttl,
            json.dumps(data),
        )

    async def get_by_phone(self, phone_number: str) -> Optional[OTPEntity]:
        """Retrieve OTP by phone number.
        
        Args:
            phone_number: The phone number to look up
            
        Returns:
            The OTP entity if found, None otherwise
        """
        key = self._get_key(phone_number)
        data = await self._redis.get(key)
        
        if not data:
            return None
        
        # Parse JSON data
        otp_data = json.loads(data)
        
        # Reconstruct OTP entity from stored data
        from datetime import datetime
        
        return OTPEntity(
            phone_number=otp_data["phone_number"],
            otp_hash=otp_data["otp_hash"],
            expires_at=datetime.fromisoformat(otp_data["expires_at"]),
            attempts=otp_data.get("attempts", 0),
        )

    async def delete_by_phone(self, phone_number: str) -> None:
        """Delete OTP for a phone number.
        
        Args:
            phone_number: The phone number to delete OTP for
        """
        key = self._get_key(phone_number)
        await self._redis.delete(key)
