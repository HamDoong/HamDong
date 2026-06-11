import uuid

from django.db import models
from django.utils import timezone


class UserRoleChoices(models.TextChoices):
    USER = "USER", "User"
    ADMIN = "ADMIN", "Admin"


class GroupTypeChoices(models.TextChoices):
    EVENT = "EVENT", "Event"
    TRIP = "TRIP", "Trip"
    GENERAL = "GENERAL", "General"


class GroupStatusChoices(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    ARCHIVED = "ARCHIVED", "Archived"
    DELETED = "DELETED", "Deleted"


class GroupMemberRoleChoices(models.TextChoices):
    OWNER = "OWNER", "Owner"
    ADMIN = "ADMIN", "Admin"
    MEMBER = "MEMBER", "Member"


class GroupMemberStatusChoices(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    LEFT = "LEFT", "Left"
    REMOVED = "REMOVED", "Removed"


class MediaFileTypeChoices(models.TextChoices):
    RECEIPT = "RECEIPT", "Receipt"
    AVATAR = "AVATAR", "Avatar"
    OTHER = "OTHER", "Other"


class MediaStorageProviderChoices(models.TextChoices):
    LOCAL = "LOCAL", "Local"
    S3 = "S3", "S3"
    MINIO = "MINIO", "MinIO"


class MediaStatusChoices(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    DELETED = "DELETED", "Deleted"


class MediaVisibilityChoices(models.TextChoices):
    GROUP_MEMBERS = "GROUP_MEMBERS", "Group Members"
    OWNER_ONLY = "OWNER_ONLY", "Owner Only"
    PRIVATE = "PRIVATE", "Private"


class MediaAccessActionChoices(models.TextChoices):
    UPLOAD = "UPLOAD", "Upload"
    VIEW = "VIEW", "View"
    DOWNLOAD = "DOWNLOAD", "Download"
    DELETE = "DELETE", "Delete"


class UserProjection(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    identity_user_id = models.UUIDField(unique=True)
    phone_number = models.CharField(max_length=32)
    display_name = models.CharField(max_length=255, null=True, blank=True)
    first_name = models.CharField(max_length=150, null=True, blank=True)
    last_name = models.CharField(max_length=150, null=True, blank=True)
    role = models.CharField(max_length=10, choices=UserRoleChoices.choices, default=UserRoleChoices.USER)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "media_user_projections"


class GroupProjection(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group_id = models.UUIDField(unique=True)
    title = models.CharField(max_length=255)
    group_type = models.CharField(max_length=20, choices=GroupTypeChoices.choices, default=GroupTypeChoices.GENERAL)
    status = models.CharField(max_length=10, choices=GroupStatusChoices.choices, default=GroupStatusChoices.ACTIVE)
    created_by_user_id = models.UUIDField()
    member_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "media_group_projections"


class GroupMemberProjection(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group_id = models.UUIDField(db_index=True)
    user_id = models.UUIDField(db_index=True)
    phone_number = models.CharField(max_length=32)
    display_name_snapshot = models.CharField(max_length=255, null=True, blank=True)
    role = models.CharField(max_length=10, choices=GroupMemberRoleChoices.choices, default=GroupMemberRoleChoices.MEMBER)
    status = models.CharField(max_length=10, choices=GroupMemberStatusChoices.choices, default=GroupMemberStatusChoices.ACTIVE)
    joined_at = models.DateTimeField(null=True, blank=True)
    left_at = models.DateTimeField(null=True, blank=True)
    removed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "media_group_member_projections"
        unique_together = (("group_id", "user_id"),)
        indexes = [models.Index(fields=["group_id"]), models.Index(fields=["user_id"])]


class MediaFile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    uploaded_by_user_id = models.UUIDField(db_index=True)
    group_id = models.UUIDField(db_index=True)
    related_expense_id = models.UUIDField(null=True, blank=True)
    file_type = models.CharField(max_length=10, choices=MediaFileTypeChoices.choices, default=MediaFileTypeChoices.RECEIPT)
    storage_provider = models.CharField(max_length=10, choices=MediaStorageProviderChoices.choices, default=MediaStorageProviderChoices.LOCAL)
    bucket_name = models.CharField(max_length=255, null=True, blank=True)
    object_key = models.CharField(max_length=512, unique=True)
    original_filename = models.CharField(max_length=255)
    stored_filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=128)
    file_extension = models.CharField(max_length=16)
    size_bytes = models.PositiveBigIntegerField()
    checksum_sha256 = models.CharField(max_length=64)
    status = models.CharField(max_length=10, choices=MediaStatusChoices.choices, default=MediaStatusChoices.ACTIVE)
    visibility = models.CharField(max_length=20, choices=MediaVisibilityChoices.choices, default=MediaVisibilityChoices.GROUP_MEMBERS)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = "media_files"


class MediaAccessLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    media_file = models.ForeignKey(MediaFile, on_delete=models.CASCADE, related_name="access_logs")
    user_id = models.UUIDField(db_index=True)
    action = models.CharField(max_length=10, choices=MediaAccessActionChoices.choices)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "media_access_logs"


class OutboxMessageStatusChoices(models.TextChoices):
    PENDING = "PENDING", "Pending"
    PUBLISHED = "PUBLISHED", "Published"
    FAILED = "FAILED", "Failed"


class OutboxMessage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_id = models.UUIDField(unique=True, db_index=True)
    event_type = models.CharField(max_length=128)
    event_version = models.PositiveIntegerField(default=1)
    source_service = models.CharField(max_length=128)
    exchange = models.CharField(max_length=128)
    routing_key = models.CharField(max_length=128)
    payload = models.JSONField(default=dict)
    status = models.CharField(max_length=20, choices=OutboxMessageStatusChoices.choices, default=OutboxMessageStatusChoices.PENDING)
    retry_count = models.PositiveIntegerField(default=0)
    last_error = models.TextField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    available_at = models.DateTimeField(default=timezone.now, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "media_outbox_messages"
        indexes = [models.Index(fields=["status", "available_at"]), models.Index(fields=["routing_key"])]



class InboxMessageStatusChoices(models.TextChoices):
    PROCESSED = "PROCESSED", "Processed"
    FAILED = "FAILED", "Failed"
    SKIPPED = "SKIPPED", "Skipped"


class InboxMessage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_id = models.UUIDField(unique=True, db_index=True)
    event_type = models.CharField(max_length=128)
    source_service = models.CharField(max_length=128)
    routing_key = models.CharField(max_length=128)
    payload = models.JSONField(default=dict)
    status = models.CharField(max_length=20, choices=InboxMessageStatusChoices.choices, default=InboxMessageStatusChoices.PROCESSED)
    processed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "media_inbox_messages"
        indexes = [models.Index(fields=["event_type"]), models.Index(fields=["routing_key"])]
