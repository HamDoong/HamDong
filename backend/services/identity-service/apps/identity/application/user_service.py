"""User management service."""

import logging
from typing import Optional

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone

from apps.identity.domain.models import User
from apps.identity.domain.rules import ArtNameRule, PhoneNumberRule
from apps.identity.infrastructure.repositories import RefreshTokenRepository, UserRepository

logger = logging.getLogger(__name__)


class UserService:
    """Service for user operations."""

    @staticmethod
    def get_or_create(phone_number: str) -> tuple[User, bool]:
        user = UserRepository.get_by_phone(phone_number)
        if user:
            return user, False

        user = UserRepository.create(
            phone_number=phone_number,
            role=User.RoleChoices.USER,
        )
        logger.info("New user created: %s", PhoneNumberRule.mask(phone_number))
        return user, True

    @staticmethod
    def get_by_id(user_id: str) -> Optional[User]:
        return UserRepository.get_by_id(user_id)

    @staticmethod
    def mark_phone_verified(user: User) -> User:
        return UserRepository.update(user, is_phone_verified=True)

    @staticmethod
    def update_last_login(user: User) -> User:
        return UserRepository.update(user, last_login_at=timezone.now())

    @staticmethod
    def update_profile(
        user: User,
        display_name: str = None,
        first_name: str = None,
        last_name: str = None,
        art_name: str = None,
    ) -> User:
        update_data = {}

        if display_name is not None:
            update_data["display_name"] = display_name
        if first_name is not None:
            update_data["first_name"] = first_name
        if last_name is not None:
            update_data["last_name"] = last_name
        if art_name is not None:
            normalized_art_name = ArtNameRule.normalize(art_name)
            if not ArtNameRule.is_valid(normalized_art_name):
                raise ValueError("INVALID_ART_NAME")
            existing = UserRepository.get_by_art_name(normalized_art_name)
            if existing and existing.id != user.id:
                raise ValueError("ART_NAME_ALREADY_EXISTS")
            update_data["art_name"] = normalized_art_name

        if update_data:
            return UserRepository.update(user, **update_data)
        return user

    @staticmethod
    def validate_new_password(user: User, raw_password: str) -> None:
        try:
            validate_password(raw_password, user=user)
        except DjangoValidationError as exc:
            raise ValueError("WEAK_PASSWORD") from exc

    @staticmethod
    def set_initial_password(user: User, raw_password: str) -> User:
        if user.has_usable_password():
            raise ValueError("PASSWORD_ALREADY_SET")
        UserService.validate_new_password(user, raw_password)
        user.set_password(raw_password)
        user.version += 1
        user.save(update_fields=["password_hash", "password_changed_at", "version", "updated_at"])
        return user

    @staticmethod
    def change_password(user: User, current_password: str, new_password: str) -> User:
        if not user.check_password(current_password):
            raise ValueError("INVALID_CURRENT_PASSWORD")
        if user.check_password(new_password):
            raise ValueError("PASSWORD_REUSE_NOT_ALLOWED")
        UserService.validate_new_password(user, new_password)
        user.set_password(new_password)
        user.version += 1
        user.save(update_fields=["password_hash", "password_changed_at", "version", "updated_at"])
        RefreshTokenRepository.revoke_active_for_user(user)
        return user
