"""User management service."""

import logging
from typing import Optional

from django.utils import timezone
from apps.identity.domain.models import User
from apps.identity.infrastructure.repositories import UserRepository

logger = logging.getLogger(__name__)


class UserService:
    """Service for user operations."""

    @staticmethod
    def get_or_create(phone_number: str) -> tuple[User, bool]:
        """
        Get existing user or create a new one.

        Returns:
            Tuple of (user, is_created)
        """
        user = UserRepository.get_by_phone(phone_number)

        if user:
            return user, False

        user = UserRepository.create(
            phone_number=phone_number,
            role=User.RoleChoices.USER,
        )
        logger.info(f"New user created: {phone_number}")
        return user, True

    @staticmethod
    def get_by_id(user_id: str) -> Optional[User]:
        """Get user by ID."""
        return UserRepository.get_by_id(user_id)

    @staticmethod
    def mark_phone_verified(user: User) -> User:
        """Mark user's phone as verified."""
        return UserRepository.update(
            user,
            is_phone_verified=True,
        )

    @staticmethod
    def update_last_login(user: User) -> User:
        """Update user's last login timestamp."""
        return UserRepository.update(
            user,
            last_login_at=timezone.now(),
        )

    @staticmethod
    def update_profile(
        user: User,
        display_name: str = None,
        first_name: str = None,
        last_name: str = None,
    ) -> User:
        """Update user profile information."""
        update_data = {}

        if display_name is not None:
            update_data["display_name"] = display_name

        if first_name is not None:
            update_data["first_name"] = first_name

        if last_name is not None:
            update_data["last_name"] = last_name

        if update_data:
            return UserRepository.update(user, **update_data)

        return user
