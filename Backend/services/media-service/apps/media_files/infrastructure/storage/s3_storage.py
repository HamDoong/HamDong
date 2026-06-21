from apps.media_files.infrastructure.storage.base import StorageProvider


class S3StorageProvider(StorageProvider):
    def save(self, file_obj, object_key: str):
        raise NotImplementedError("S3 storage is not implemented in Phase 6")

    def open(self, object_key: str):
        raise NotImplementedError("S3 storage is not implemented in Phase 6")

    def delete(self, object_key: str):
        raise NotImplementedError("S3 storage is not implemented in Phase 6")

    def exists(self, object_key: str) -> bool:
        raise NotImplementedError("S3 storage is not implemented in Phase 6")

    def generate_url(self, object_key: str) -> str:
        raise NotImplementedError("S3 storage is not implemented in Phase 6")
