from __future__ import annotations

import uuid

from django.db import models


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


class InboxMessageStatusChoices(models.TextChoices):
    PROCESSED = "PROCESSED", "Processed"
    SKIPPED = "SKIPPED", "Skipped"
    FAILED = "FAILED", "Failed"


class DashboardActivityTypeChoices(models.TextChoices):
    GROUP_CREATED = "GROUP_CREATED", "Group Created"
    GROUP_MEMBER_JOINED = "GROUP_MEMBER_JOINED", "Group Member Joined"
    GROUP_INVITATION_CREATED = "GROUP_INVITATION_CREATED", "Group Invitation Created"
    EXPENSE_CREATED = "EXPENSE_CREATED", "Expense Created"
    EXPENSE_UPDATED = "EXPENSE_UPDATED", "Expense Updated"
    EXPENSE_DELETED = "EXPENSE_DELETED", "Expense Deleted"
    RECEIPT_UPLOADED = "RECEIPT_UPLOADED", "Receipt Uploaded"
    SETTLEMENT_REPORTED = "SETTLEMENT_REPORTED", "Settlement Reported"
    SETTLEMENT_CONFIRMED = "SETTLEMENT_CONFIRMED", "Settlement Confirmed"
    SETTLEMENT_REJECTED = "SETTLEMENT_REJECTED", "Settlement Rejected"
    SETTLEMENT_PLAN_ACTIVATED = "SETTLEMENT_PLAN_ACTIVATED", "Settlement Plan Activated"
    WALLET_PAYMENT_COMPLETED = "WALLET_PAYMENT_COMPLETED", "Wallet Payment Completed"


class UserProjection(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    identity_user_id = models.UUIDField(unique=True)
    email = models.EmailField(blank=True)
    art_name = models.CharField(max_length=255, null=True, blank=True)
    first_name = models.CharField(max_length=100, null=True, blank=True)
    last_name = models.CharField(max_length=100, null=True, blank=True)
    role = models.CharField(max_length=32, default="USER")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class GroupProjection(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group_id = models.UUIDField(unique=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    group_type = models.CharField(max_length=32, default="GENERAL")
    status = models.CharField(max_length=32, choices=GroupStatusChoices.choices, default=GroupStatusChoices.ACTIVE)
    created_by_user_id = models.UUIDField(null=True, blank=True)
    member_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class GroupMemberProjection(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group_id = models.UUIDField(db_index=True)
    user_id = models.UUIDField(db_index=True)
    email = models.EmailField(blank=True)
    art_name_snapshot = models.CharField(max_length=255, null=True, blank=True)
    role = models.CharField(max_length=32, choices=GroupMemberRoleChoices.choices, default=GroupMemberRoleChoices.MEMBER)
    status = models.CharField(max_length=32, choices=GroupMemberStatusChoices.choices, default=GroupMemberStatusChoices.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["group_id", "user_id"], name="dashboard_unique_group_member")
        ]
        indexes = [
            models.Index(fields=["user_id", "status"]),
            models.Index(fields=["group_id", "status"]),
        ]


class DashboardActivity(models.Model):
    id = models.UUIDField(primary_key=True, editable=False)
    event_type = models.CharField(max_length=64, choices=DashboardActivityTypeChoices.choices)
    source_service = models.CharField(max_length=64)
    routing_key = models.CharField(max_length=128)
    group_id = models.UUIDField(db_index=True)
    actor_user_id = models.UUIDField(null=True, blank=True, db_index=True)
    source_object_id = models.UUIDField(null=True, blank=True, db_index=True)
    summary = models.JSONField(default=dict, blank=True)
    occurred_at = models.DateTimeField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["group_id", "occurred_at"]),
            models.Index(fields=["event_type", "occurred_at"]),
        ]


class InboxMessage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_id = models.UUIDField(unique=True)
    event_type = models.CharField(max_length=128)
    source_service = models.CharField(max_length=64)
    routing_key = models.CharField(max_length=128)
    payload = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=16, choices=InboxMessageStatusChoices.choices, default=InboxMessageStatusChoices.PROCESSED)
    error_message = models.TextField(blank=True, default="")
    processed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
