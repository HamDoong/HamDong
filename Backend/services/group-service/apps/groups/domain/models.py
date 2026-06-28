import uuid

from django.db import models
from django.db.models import Q
from django.utils import timezone


class UserProjection(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    identity_user_id = models.UUIDField(unique=True)
    email = models.CharField(max_length=254)
    art_name = models.CharField(max_length=255, null=True, blank=True)
    first_name = models.CharField(max_length=255, null=True, blank=True)
    last_name = models.CharField(max_length=255, null=True, blank=True)
    role = models.CharField(max_length=32, default="USER")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "groups_user_projections"


class GroupTypeChoices(models.TextChoices):
    EVENT = "EVENT", "Event"
    TRIP = "TRIP", "Trip"
    GENERAL = "GENERAL", "General"


class GroupStatusChoices(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    ARCHIVED = "ARCHIVED", "Archived"
    DELETED = "DELETED", "Deleted"


class Group(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    title_parts = models.JSONField(default=list, blank=True)
    description = models.TextField(null=True, blank=True)
    group_type = models.CharField(max_length=32, choices=GroupTypeChoices.choices)
    status = models.CharField(
        max_length=32,
        choices=GroupStatusChoices.choices,
        default=GroupStatusChoices.ACTIVE,
    )
    created_by_user_id = models.UUIDField()
    created_by_email = models.CharField(max_length=254)
    deleted_by_user_id = models.UUIDField(null=True, blank=True)
    member_count = models.PositiveIntegerField(default=0)
    version = models.PositiveIntegerField(default=1)
    restored_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "groups"

    @property
    def display_title(self) -> str:
        if self.title:
            return self.title
        return " ".join([part for part in self.title_parts if part]).strip()


class GroupMemberRoleChoices(models.TextChoices):
    OWNER = "OWNER", "Owner"
    ADMIN = "ADMIN", "Admin"
    MEMBER = "MEMBER", "Member"


class GroupMemberStatusChoices(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    LEFT = "LEFT", "Left"
    REMOVED = "REMOVED", "Removed"


class GroupMember(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="members")
    user_id = models.UUIDField()
    email = models.CharField(max_length=254)
    art_name_snapshot = models.CharField(max_length=255, null=True, blank=True)
    role = models.CharField(max_length=16, choices=GroupMemberRoleChoices.choices)
    status = models.CharField(max_length=16, choices=GroupMemberStatusChoices.choices, default=GroupMemberStatusChoices.ACTIVE)
    joined_at = models.DateTimeField(auto_now_add=True)
    left_at = models.DateTimeField(null=True, blank=True)
    removed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "group_members"
        constraints = [
            models.UniqueConstraint(fields=["group", "user_id"], name="group_member_unique_group_user"),
        ]


class GroupInviteTypeChoices(models.TextChoices):
    TOKEN = "TOKEN", "Token"
    DIRECT = "DIRECT", "Direct"


class GroupInviteStatusChoices(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    USED = "USED", "Used"
    REVOKED = "REVOKED", "Revoked"
    EXPIRED = "EXPIRED", "Expired"
    PENDING = "PENDING", "Pending"
    ACCEPTED = "ACCEPTED", "Accepted"
    REJECTED = "REJECTED", "Rejected"


class GroupInvite(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="invites")
    invite_type = models.CharField(max_length=16, choices=GroupInviteTypeChoices.choices, default=GroupInviteTypeChoices.TOKEN)
    created_by_user_id = models.UUIDField()
    token_hash = models.CharField(max_length=128, null=True, blank=True)
    invite_code = models.CharField(max_length=64, null=True, blank=True)
    recipient_user_id = models.UUIDField(null=True, blank=True, db_index=True)
    recipient_email = models.CharField(max_length=254, null=True, blank=True)
    status = models.CharField(max_length=16, choices=GroupInviteStatusChoices.choices, default=GroupInviteStatusChoices.ACTIVE)
    max_uses = models.PositiveIntegerField(null=True, blank=True)
    used_count = models.PositiveIntegerField(default=0)
    expires_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "group_invites"
        indexes = [
            models.Index(fields=["group", "invite_type", "status"], name="group_invite_type_status_idx"),
            models.Index(fields=["recipient_user_id", "invite_type", "status"], name="group_invite_recipient_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(invite_type=GroupInviteTypeChoices.TOKEN, token_hash__isnull=False)
                    | Q(invite_type=GroupInviteTypeChoices.DIRECT, recipient_user_id__isnull=False)
                ),
                name="group_invite_type_required_fields",
            ),
        ]

    @property
    def is_direct(self) -> bool:
        return self.invite_type == GroupInviteTypeChoices.DIRECT

    @property
    def is_token(self) -> bool:
        return self.invite_type == GroupInviteTypeChoices.TOKEN


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
        db_table = "groups_outbox_messages"
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
        db_table = "groups_inbox_messages"
        indexes = [models.Index(fields=["event_type"]), models.Index(fields=["routing_key"])]
