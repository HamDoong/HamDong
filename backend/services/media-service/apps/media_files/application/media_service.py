import hashlib
import uuid
from datetime import datetime, timezone
from io import BytesIO

from apps.media_files.application.file_validator import GroupNotFoundError, MediaFileNotFoundError, MediaPermissionDeniedError, NotGroupMemberError
from apps.media_files.domain.models import MediaStatusChoices
from apps.media_files.domain.rules import can_access_media, can_manage_media
from apps.media_files.infrastructure.repositories import GroupMemberProjectionRepository, GroupProjectionRepository, MediaAccessLogRepository, MediaFileRepository
from apps.media_files.infrastructure.storage.local_storage import LocalStorageProvider


class MediaService:
    def __init__(self, storage_provider=None):
        self.storage_provider = storage_provider or LocalStorageProvider()

    def _get_group_or_raise(self, group_id):
        group = GroupProjectionRepository.get(group_id)
        if not group:
            raise GroupNotFoundError()
        if group.status != "ACTIVE":
            raise MediaPermissionDeniedError()
        return group

    def _get_active_member_or_raise(self, group_id, user_id):
        member = GroupMemberProjectionRepository.get_active_member(group_id, user_id)
        if not member:
            raise NotGroupMemberError()
        return member

    def _get_media_or_raise(self, media_file_id):
        media_file = MediaFileRepository.get(media_file_id)
        if not media_file:
            raise MediaFileNotFoundError()
        return media_file

    def build_object_key(self, group_id, file_extension):
        now = datetime.now(timezone.utc)
        file_uuid = uuid.uuid4()
        return f"receipts/{group_id}/{now.year}/{now.month:02d}/{file_uuid}.{file_extension.lower()}"

    def checksum(self, content_bytes: bytes) -> str:
        return hashlib.sha256(content_bytes).hexdigest()

    def read_uploaded_file(self, uploaded_file) -> bytes:
        if hasattr(uploaded_file, "chunks"):
            data = b"".join(chunk for chunk in uploaded_file.chunks())
        else:
            data = uploaded_file.read()
        if hasattr(uploaded_file, "seek"):
            uploaded_file.seek(0)
        return data

    def save_blob(self, uploaded_file, object_key: str):
        content_bytes = self.read_uploaded_file(uploaded_file)
        return self.storage_provider.save(BytesIO(content_bytes), object_key), content_bytes

    def to_metadata(self, media_file):
        return {
            "id": str(media_file.id),
            "group_id": str(media_file.group_id),
            "related_expense_id": str(media_file.related_expense_id) if media_file.related_expense_id else None,
            "file_type": media_file.file_type,
            "original_filename": media_file.original_filename,
            "content_type": media_file.content_type,
            "size_bytes": media_file.size_bytes,
            "status": media_file.status,
            "visibility": media_file.visibility,
            "created_at": media_file.created_at.isoformat(),
        }

    def upload_access_log(self, media_file, user_id, action, request=None):
        ip_address = None
        user_agent = None
        if request is not None:
            ip_address = request.META.get("REMOTE_ADDR")
            user_agent = request.META.get("HTTP_USER_AGENT")
        return MediaAccessLogRepository.create(media_file, user_id, action, ip_address=ip_address, user_agent=user_agent)

    def ensure_view_access(self, media_file, user_id):
        if media_file.status != MediaStatusChoices.ACTIVE:
            raise MediaFileNotFoundError()
        if not can_access_media(media_file, user_id):
            raise MediaPermissionDeniedError()

    def ensure_delete_access(self, media_file, user_id):
        if media_file.status != MediaStatusChoices.ACTIVE:
            raise MediaFileNotFoundError()
        if not can_manage_media(media_file, user_id):
            raise MediaPermissionDeniedError()

    def get_file_handle(self, media_file):
        return self.storage_provider.open(media_file.object_key)
