from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings
from django.core.files.storage import default_storage


ALLOWED_AVATAR_CONTENT_TYPES = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}
MAX_AVATAR_FILE_SIZE_BYTES = 5 * 1024 * 1024


@dataclass(frozen=True)
class StoredAvatar:
    file_id: uuid.UUID
    storage_path: str
    public_url: str


class AvatarStorageError(RuntimeError):
    pass


def _sniff_image_extension(uploaded_file) -> str:
    header = uploaded_file.read(16)
    uploaded_file.seek(0)
    if header.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if header[:4] == b"RIFF" and header[8:12] == b"WEBP":
        return "webp"
    raise AvatarStorageError("INVALID_AVATAR_FILE_TYPE")


class AvatarStorage:
    def validate(self, uploaded_file) -> str:
        if uploaded_file is None:
            raise AvatarStorageError("AVATAR_FILE_REQUIRED")
        if getattr(uploaded_file, "size", 0) > MAX_AVATAR_FILE_SIZE_BYTES:
            raise AvatarStorageError("AVATAR_FILE_TOO_LARGE")
        content_type = str(getattr(uploaded_file, "content_type", "") or "").lower()
        if content_type not in ALLOWED_AVATAR_CONTENT_TYPES:
            raise AvatarStorageError("INVALID_AVATAR_FILE_TYPE")
        extension = _sniff_image_extension(uploaded_file)
        if ALLOWED_AVATAR_CONTENT_TYPES[content_type] != extension:
            raise AvatarStorageError("INVALID_AVATAR_FILE_TYPE")
        return extension

    def save(self, *, user_id, uploaded_file, request, file_id: uuid.UUID | None = None) -> StoredAvatar:
        extension = self.validate(uploaded_file)
        file_id = file_id or uuid.uuid4()
        storage_path = f"avatars/{user_id}/{file_id}.{extension}"
        uploaded_file.seek(0)
        try:
            if default_storage.exists(storage_path):
                default_storage.delete(storage_path)
            default_storage.save(storage_path, uploaded_file)
        except Exception as exc:  # pragma: no cover - defensive
            raise AvatarStorageError("AVATAR_STORAGE_FAILED") from exc
        public_url = request.build_absolute_uri(f"{settings.MEDIA_URL}{storage_path}")
        return StoredAvatar(file_id=file_id, storage_path=storage_path, public_url=public_url)

    def delete(self, *, user_id, file_id: uuid.UUID | str | None) -> None:
        if not file_id:
            return
        avatar_dir = Path(settings.MEDIA_ROOT) / "avatars" / str(user_id)
        if not avatar_dir.exists():
            return
        for candidate in avatar_dir.glob(f"{file_id}.*"):
            try:
                default_storage.delete(str(candidate.relative_to(settings.MEDIA_ROOT)))
            except Exception:
                try:
                    candidate.unlink(missing_ok=True)
                except Exception:
                    continue
