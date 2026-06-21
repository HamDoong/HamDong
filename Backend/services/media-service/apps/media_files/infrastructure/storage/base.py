from abc import ABC, abstractmethod

from apps.media_files.domain.value_objects import StoredFileResult


class StorageProvider(ABC):
    @abstractmethod
    def save(self, file_obj, object_key: str) -> StoredFileResult:
        raise NotImplementedError

    @abstractmethod
    def open(self, object_key: str):
        raise NotImplementedError

    @abstractmethod
    def delete(self, object_key: str):
        raise NotImplementedError

    @abstractmethod
    def exists(self, object_key: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def generate_url(self, object_key: str) -> str:
        raise NotImplementedError
