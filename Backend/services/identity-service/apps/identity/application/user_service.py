"""User management service."""

from __future__ import annotations

import logging
import uuid
from typing import Any, Optional

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.identity.domain.models import User
from apps.identity.domain.rules import ArtNameRule, DateOfBirthRule, EmailRule, PhoneNumberRule, ProfileRule
from apps.identity.infrastructure.repositories import RefreshTokenRepository, UserRepository

logger = logging.getLogger(__name__)


class UserService:
    """Service for user operations."""

    PROFILE_FIELDS = {
        "display_name",
        "phone_number",
        "date_of_birth",
        "city",
        "bio",
        "avatar_url",
        "first_name",
        "last_name",
        "art_name",
    }

    @staticmethod
    def _build_art_name_candidate(value: str | None, user_id: str | None = None) -> str:
        candidate = ArtNameRule.sanitize_candidate(value)
        if candidate and ArtNameRule.is_valid(candidate):
            return candidate
        suffix = (str(user_id or uuid.uuid4()).replace("-", "")[:8]).lower()
        return f"user-{suffix}"[:32]

    @staticmethod
    def _generate_unique_art_name(seed: str | None, user_id: str | None = None) -> str:
        candidate = UserService._build_art_name_candidate(seed, user_id=user_id)
        existing = UserRepository.get_by_art_name(candidate)
        if not existing or str(existing.id) == str(user_id):
            return candidate
        suffix = (str(user_id or uuid.uuid4()).replace("-", "")[:6]).lower()
        base = candidate[: max(3, 32 - len(suffix) - 1)].rstrip("-")
        candidate = f"{base}-{suffix}"
        existing = UserRepository.get_by_art_name(candidate)
        if not existing or str(existing.id) == str(user_id):
            return candidate
        return f"user-{suffix}"[:32]

    @staticmethod
    def get_or_create(email: str) -> tuple[User, bool]:
        normalized_email = EmailRule.normalize(email)
        user = UserRepository.get_by_email(normalized_email) if normalized_email else None
        if user:
            if not user.art_name:
                user = UserRepository.update(
                    user,
                    art_name=UserService._generate_unique_art_name(
                        normalized_email.split("@", 1)[0], user.id
                    ),
                )
            return user, False

        if not normalized_email:
            raise ValueError("INVALID_EMAIL")

        art_name = UserService._generate_unique_art_name(normalized_email.split("@", 1)[0])
        user = UserRepository.create(
            email=normalized_email,
            art_name=art_name,
            role=User.RoleChoices.USER,
        )
        logger.info("New user created: %s", EmailRule.mask(normalized_email))
        return user, True

    @staticmethod
    def get_by_id(user_id: str) -> Optional[User]:
        return UserRepository.get_by_id(user_id)

    @staticmethod
    def mark_email_verified(user: User) -> User:
        if user.is_email_verified:
            return user
        return UserRepository.update(user, is_email_verified=True)

    @staticmethod
    def update_last_login(user: User) -> User:
        return UserRepository.update(user, last_login_at=timezone.now())

    @staticmethod
    def _normalize_profile_updates(user: User, **kwargs: Any) -> dict[str, Any]:
        update_data: dict[str, Any] = {}

        if "first_name" in kwargs:
            update_data["first_name"] = ProfileRule.normalize_optional_text(
                kwargs["first_name"],
                max_length=150,
                field_name="first_name",
            )
        if "last_name" in kwargs:
            update_data["last_name"] = ProfileRule.normalize_optional_text(
                kwargs["last_name"],
                max_length=150,
                field_name="last_name",
            )
        if "display_name" in kwargs:
            update_data["display_name"] = ProfileRule.normalize_display_name(kwargs["display_name"])
        if "city" in kwargs:
            update_data["city"] = ProfileRule.normalize_city(kwargs["city"])
        if "bio" in kwargs:
            update_data["bio"] = ProfileRule.normalize_bio(kwargs["bio"])
        if "avatar_url" in kwargs:
            update_data["avatar_url"] = kwargs["avatar_url"]
        if "date_of_birth" in kwargs:
            update_data["date_of_birth"] = DateOfBirthRule.validate(kwargs["date_of_birth"])
        if "phone_number" in kwargs:
            normalized_phone = PhoneNumberRule.normalize(kwargs["phone_number"])
            existing_by_phone = UserRepository.get_by_phone_number(normalized_phone) if normalized_phone else None
            if existing_by_phone and existing_by_phone.id != user.id:
                raise ValueError("PHONE_NUMBER_ALREADY_EXISTS")
            update_data["phone_number"] = normalized_phone
        if "art_name" in kwargs:
            normalized_art_name = ArtNameRule.normalize(kwargs["art_name"])
            if not ArtNameRule.is_valid(normalized_art_name):
                raise ValueError("INVALID_ART_NAME")
            existing = UserRepository.get_by_art_name(normalized_art_name)
            if existing and existing.id != user.id:
                raise ValueError("ART_NAME_ALREADY_EXISTS")
            update_data["art_name"] = normalized_art_name

        return update_data

    @staticmethod
    def update_profile(user: User, **kwargs: Any) -> User:
        update_data = UserService._normalize_profile_updates(user, **kwargs)
        if not update_data:
            return user
        try:
            with transaction.atomic():
                return UserRepository.update(user, **update_data)
        except IntegrityError as exc:
            raise ValueError("PROFILE_CONFLICT") from exc

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
    def change_password(user: User, current_password: str, new_password: str, *, current_jti: str | None = None) -> tuple[User, int]:
        if not user.check_password(current_password):
            raise ValueError("INVALID_CURRENT_PASSWORD")
        if user.check_password(new_password):
            raise ValueError("PASSWORD_REUSE_NOT_ALLOWED")
        UserService.validate_new_password(user, new_password)
        with transaction.atomic():
            user.set_password(new_password)
            user.version += 1
            user.save(update_fields=["password_hash", "password_changed_at", "version", "updated_at"])
            revoked_count = RefreshTokenRepository.revoke_other_active_for_user(user, current_jti=current_jti)
        return user, revoked_count
