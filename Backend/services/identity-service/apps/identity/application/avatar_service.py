from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction

from apps.identity.domain.events import UserUpdated
from apps.identity.domain.models import User
from apps.identity.infrastructure.avatar_storage import AvatarStorage, AvatarStorageError
from apps.identity.infrastructure.rabbitmq_publisher import RabbitMqPublisher
from apps.identity.infrastructure.repositories import UserRepository


@dataclass
class AvatarError(ValueError):
    code: str
    message: str

    def __str__(self) -> str:
        return self.code


class AvatarService:
    def __init__(self):
        self.storage = AvatarStorage()
        self.publisher = RabbitMqPublisher()

    @staticmethod
    def serialize_avatar(user: User) -> dict:
        has_avatar = bool(user.avatar_url)
        return {
            "avatar_url": user.avatar_url if has_avatar else None,
            "file_id": str(user.avatar_file_id) if getattr(user, "avatar_file_id", None) else None,
            "updated_at": user.updated_at if has_avatar else None,
        }

    @staticmethod
    def serialize_avatar_user(user: User) -> dict:
        return {
            "id": str(user.id),
            "art_name": user.art_name,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "avatar_url": user.avatar_url,
        }

    @staticmethod
    def ensure_active(user: User) -> None:
        if not user.is_active or user.deleted_at is not None:
            raise AvatarError(
                "ACCOUNT_DEACTIVATED",
                "This account has been deactivated.",
            )

    def _publish_user_updated(self, user: User) -> None:
        event = UserUpdated(
            user_id=user.id,
            email=user.email,
            art_name=user.art_name,
            first_name=user.first_name,
            last_name=user.last_name,
            display_name=user.display_name,
            avatar_url=user.avatar_url,
            role=user.role,
            is_active=user.is_active,
        )
        self.publisher.publish(event.to_dict(), "identity.user.updated")

    @transaction.atomic
    def upload(self, *, user: User, uploaded_file, request) -> dict:
        self.ensure_active(user)
        previous_file_id = getattr(user, "avatar_file_id", None)
        try:
            stored = self.storage.save(user_id=user.id, uploaded_file=uploaded_file, request=request)
        except AvatarStorageError as exc:
            raise AvatarError(exc.args[0], self._message_for_code(exc.args[0])) from exc

        updated_user = UserRepository.update(
            user,
            avatar_url=stored.public_url,
            avatar_file_id=stored.file_id,
        )
        if previous_file_id and str(previous_file_id) != str(stored.file_id):
            self.storage.delete(user_id=user.id, file_id=previous_file_id)
        self._publish_user_updated(updated_user)
        payload = self.serialize_avatar(updated_user)
        payload["user"] = self.serialize_avatar_user(updated_user)
        return payload

    @transaction.atomic
    def delete(self, *, user: User) -> dict:
        self.ensure_active(user)
        previous_file_id = getattr(user, "avatar_file_id", None)
        had_avatar = bool(user.avatar_url or previous_file_id)
        if previous_file_id:
            self.storage.delete(user_id=user.id, file_id=previous_file_id)
        updated_user = UserRepository.update(
            user,
            avatar_url=None,
            avatar_file_id=None,
        )
        if had_avatar:
            self._publish_user_updated(updated_user)
        payload = self.serialize_avatar(updated_user)
        payload["updated_at"] = updated_user.updated_at if had_avatar else None
        payload["message"] = "Profile avatar has been removed successfully."
        payload["user"] = self.serialize_avatar_user(updated_user)
        return payload

    @staticmethod
    def _message_for_code(code: str) -> str:
        return {
            "AVATAR_FILE_REQUIRED": "Avatar image file is required.",
            "INVALID_AVATAR_FILE_TYPE": "Only JPEG, PNG, and WebP images are allowed.",
            "AVATAR_FILE_TOO_LARGE": "Avatar image must be 5MB or smaller.",
            "AVATAR_STORAGE_FAILED": "Could not store avatar image.",
        }.get(code, "Could not process avatar image.")
