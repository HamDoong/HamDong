from dataclasses import dataclass


@dataclass(frozen=True)
class StoredFileResult:
    object_key: str
    absolute_path: str
    url: str
    size_bytes: int
