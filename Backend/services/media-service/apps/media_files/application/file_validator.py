from dataclasses import dataclass


class MediaServiceError(Exception):
    code = "MEDIA_SERVICE_ERROR"
    message = "A media service error occurred."
    status_code = 400

    def __init__(self, message=None):
        super().__init__(message or self.message)
        if message:
            self.message = message


class FileTooLargeError(MediaServiceError):
    code = "FILE_TOO_LARGE"
    message = "Uploaded file is too large."
    status_code = 400


class InvalidFileTypeError(MediaServiceError):
    code = "INVALID_FILE_TYPE"
    message = "Uploaded file type is not allowed."
    status_code = 400


class MediaFileNotFoundError(MediaServiceError):
    code = "MEDIA_FILE_NOT_FOUND"
    message = "Media file was not found."
    status_code = 404


class GroupNotFoundError(MediaServiceError):
    code = "GROUP_NOT_FOUND"
    message = "Group was not found."
    status_code = 404


class NotGroupMemberError(MediaServiceError):
    code = "NOT_GROUP_MEMBER"
    message = "You are not an active member of this group."
    status_code = 403


class MediaPermissionDeniedError(MediaServiceError):
    code = "MEDIA_PERMISSION_DENIED"
    message = "You do not have permission to access this media file."
    status_code = 403


@dataclass(frozen=True)
class ValidatedUpload:
    original_filename: str
    file_extension: str
    content_type: str
    size_bytes: int


class FileValidator:
    BLOCKED_EXTENSIONS = {
        "exe",
        "bat",
        "cmd",
        "com",
        "scr",
        "ps1",
        "sh",
        "bash",
        "zsh",
        "dll",
        "so",
        "dylib",
        "js",
        "mjs",
        "cjs",
        "php",
        "py",
        "rb",
        "pl",
        "jar",
        "apk",
    }

    def __init__(self, max_size_bytes, allowed_extensions, allowed_content_types):
        self.max_size_bytes = max_size_bytes
        self.allowed_extensions = {ext.lower() for ext in allowed_extensions}
        self.allowed_content_types = {content_type.lower() for content_type in allowed_content_types}

    def _normalize_extension(self, filename: str) -> str:
        if not filename:
            return ""
        name = filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1].strip()
        if "." not in name:
            return ""
        return name.rsplit(".", 1)[-1].lower().strip()

    def validate(self, uploaded_file) -> ValidatedUpload:
        original_filename = getattr(uploaded_file, "name", "") or ""
        size_bytes = int(getattr(uploaded_file, "size", 0) or 0)
        content_type = (getattr(uploaded_file, "content_type", "") or "").lower()
        extension = self._normalize_extension(original_filename)

        if size_bytes > self.max_size_bytes:
            raise FileTooLargeError()
        if not extension or extension in self.BLOCKED_EXTENSIONS or extension not in self.allowed_extensions:
            raise InvalidFileTypeError()
        if content_type not in self.allowed_content_types:
            raise InvalidFileTypeError()

        return ValidatedUpload(original_filename=original_filename, file_extension=extension, content_type=content_type, size_bytes=size_bytes)
