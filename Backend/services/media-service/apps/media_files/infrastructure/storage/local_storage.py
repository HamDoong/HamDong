from pathlib import Path

from django.conf import settings

from apps.media_files.domain.value_objects import StoredFileResult
from apps.media_files.infrastructure.storage.base import StorageProvider


class LocalStorageProvider(StorageProvider):
    def __init__(self, root=None):
        self.root = Path(root or settings.MEDIA_ROOT)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, object_key: str) -> Path:
        candidate = Path(object_key)
        if candidate.is_absolute():
            raise ValueError("object_key must be relative")
        normalized = candidate.as_posix().lstrip("/")
        full_path = (self.root / normalized).resolve()
        root_path = self.root.resolve()
        if full_path != root_path and root_path not in full_path.parents:
            raise ValueError("object_key escapes media root")
        return full_path

    def save(self, file_obj, object_key: str) -> StoredFileResult:
        path = self._path(object_key)
        path.parent.mkdir(parents=True, exist_ok=True)
        if hasattr(file_obj, "read"):
            content = file_obj.read()
        else:
            content = bytes(file_obj)
        with path.open("wb") as fh:
            fh.write(content)
        return StoredFileResult(object_key=object_key, absolute_path=str(path), url=self.generate_url(object_key), size_bytes=len(content))

    def open(self, object_key: str):
        return self._path(object_key).open("rb")

    def delete(self, object_key: str):
        path = self._path(object_key)
        if path.exists():
            path.unlink()

    def exists(self, object_key: str) -> bool:
        return self._path(object_key).exists()

    def generate_url(self, object_key: str) -> str:
        normalized_key = Path(object_key).as_posix().lstrip("/")
        return f"{settings.MEDIA_URL}{normalized_key}"
