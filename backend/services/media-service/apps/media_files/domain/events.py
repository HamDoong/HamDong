import uuid
from datetime import datetime, timezone


class DomainEvent:
    def __init__(self, event_type: str, data: dict, version: int = 1):
        self.event_id = str(uuid.uuid4())
        self.event_type = event_type
        self.occurred_at = datetime.now(timezone.utc)
        self.version = version
        self.data = data

    def to_dict(self):
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "occurred_at": self.occurred_at.isoformat(),
            "version": self.version,
            "data": self.data,
        }


class MediaUploaded(DomainEvent):
    def __init__(self, media_file_id, group_id, related_expense_id, uploaded_by_user_id, file_type, content_type, size_bytes):
        super().__init__(
            "MediaUploaded",
            {
                "media_file_id": str(media_file_id),
                "group_id": str(group_id),
                "related_expense_id": str(related_expense_id) if related_expense_id else None,
                "uploaded_by_user_id": str(uploaded_by_user_id),
                "file_type": file_type,
                "content_type": content_type,
                "size_bytes": size_bytes,
            },
        )


class MediaDeleted(DomainEvent):
    def __init__(self, media_file_id, group_id, deleted_by_user_id):
        super().__init__(
            "MediaDeleted",
            {
                "media_file_id": str(media_file_id),
                "group_id": str(group_id),
                "deleted_by_user_id": str(deleted_by_user_id),
            },
        )
