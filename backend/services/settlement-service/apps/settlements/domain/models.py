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


class CurrencyChoices(models.TextChoices):
    IRR = "IRR", "Iranian Rial"


class ExpenseStatusChoices(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    UPDATED = "UPDATED", "Updated"
    DELETED = "DELETED", "Deleted"


class DebtLedgerEntryTypeChoices(models.TextChoices):
    EXPENSE_SHARE = "EXPENSE_SHARE", "Expense Share"
    EXPENSE_REVERSAL = "EXPENSE_REVERSAL", "Expense Reversal"
    MANUAL_SETTLEMENT = "MANUAL_SETTLEMENT", "Manual Settlement"


class DebtLedgerStatusChoices(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    REVERSED = "REVERSED", "Reversed"
    DELETED = "DELETED", "Deleted"


class ManualSettlementStatusChoices(models.TextChoices):
    PENDING_CONFIRMATION = "PENDING_CONFIRMATION", "Pending Confirmation"
    CONFIRMED = "CONFIRMED", "Confirmed"
    REJECTED = "REJECTED", "Rejected"
    CANCELLED = "CANCELLED", "Cancelled"


class SettlementPlanStatusChoices(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    ACTIVE = "ACTIVE", "Active"
    COMPLETED = "COMPLETED", "Completed"
    CANCELLED = "CANCELLED", "Cancelled"
    EXPIRED = "EXPIRED", "Expired"


class SettlementPlanItemStatusChoices(models.TextChoices):
    PENDING = "PENDING", "Pending"
    REPORTED = "REPORTED", "Reported"
    CONFIRMED = "CONFIRMED", "Confirmed"
    REJECTED = "REJECTED", "Rejected"
    CANCELLED = "CANCELLED", "Cancelled"


class SettlementPlanEventTypeChoices(models.TextChoices):
    PLAN_GENERATED = "PLAN_GENERATED", "Plan Generated"
    PLAN_ACTIVATED = "PLAN_ACTIVATED", "Plan Activated"
    PLAN_CANCELLED = "PLAN_CANCELLED", "Plan Cancelled"
    PLAN_EXPIRED = "PLAN_EXPIRED", "Plan Expired"
    ITEM_REPORTED = "ITEM_REPORTED", "Item Reported"
    ITEM_CONFIRMED = "ITEM_CONFIRMED", "Item Confirmed"
    ITEM_REJECTED = "ITEM_REJECTED", "Item Rejected"
    ITEM_CANCELLED = "ITEM_CANCELLED", "Item Cancelled"
    PLAN_COMPLETED = "PLAN_COMPLETED", "Plan Completed"


class UserProjection(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    identity_user_id = models.UUIDField(unique=True, db_index=True)
    phone_number = models.CharField(max_length=32)
    display_name = models.CharField(max_length=255, null=True, blank=True)
    first_name = models.CharField(max_length=150, null=True, blank=True)
    last_name = models.CharField(max_length=150, null=True, blank=True)
    role = models.CharField(
        max_length=10, choices=UserRoleChoices.choices, default=UserRoleChoices.USER
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "settlement_user_projections"


class GroupProjection(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group_id = models.UUIDField(unique=True, db_index=True)
    title = models.CharField(max_length=255)
    group_type = models.CharField(
        max_length=20,
        choices=GroupTypeChoices.choices,
        default=GroupTypeChoices.GENERAL,
    )
    status = models.CharField(
        max_length=10,
        choices=GroupStatusChoices.choices,
        default=GroupStatusChoices.ACTIVE,
    )
    created_by_user_id = models.UUIDField()
    member_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "settlement_group_projections"


class GroupMemberProjection(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group_id = models.UUIDField(db_index=True)
    user_id = models.UUIDField(db_index=True)
    phone_number = models.CharField(max_length=32)
    display_name_snapshot = models.CharField(max_length=255, null=True, blank=True)
    role = models.CharField(
        max_length=10,
        choices=GroupMemberRoleChoices.choices,
        default=GroupMemberRoleChoices.MEMBER,
    )
    status = models.CharField(
        max_length=10,
        choices=GroupMemberStatusChoices.choices,
        default=GroupMemberStatusChoices.ACTIVE,
    )
    joined_at = models.DateTimeField(null=True, blank=True)
    left_at = models.DateTimeField(null=True, blank=True)
    removed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "settlement_group_member_projections"
        unique_together = (("group_id", "user_id"),)
        indexes = [models.Index(fields=["group_id"]), models.Index(fields=["user_id"])]


class ExpenseProjection(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    expense_id = models.UUIDField(unique=True, db_index=True)
    group_id = models.UUIDField(db_index=True)
    created_by_user_id = models.UUIDField()
    payer_user_id = models.UUIDField(db_index=True)
    currency = models.CharField(
        max_length=3, choices=CurrencyChoices.choices, default=CurrencyChoices.IRR
    )
    base_amount_minor = models.BigIntegerField(default=0)
    tax_amount_minor = models.BigIntegerField(default=0)
    service_fee_amount_minor = models.BigIntegerField(default=0)
    total_amount_minor = models.BigIntegerField(default=0)
    status = models.CharField(
        max_length=10,
        choices=ExpenseStatusChoices.choices,
        default=ExpenseStatusChoices.ACTIVE,
    )
    expense_version = models.PositiveIntegerField(default=1)
    expense_date = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "settlement_expense_projections"


class ExpenseParticipantProjection(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    expense_id = models.UUIDField(db_index=True)
    group_id = models.UUIDField(db_index=True)
    user_id = models.UUIDField(db_index=True)
    base_share_minor = models.BigIntegerField(default=0)
    tax_share_minor = models.BigIntegerField(default=0)
    service_fee_share_minor = models.BigIntegerField(default=0)
    total_share_minor = models.BigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "settlement_expense_participant_projections"
        unique_together = (("expense_id", "user_id"),)
        indexes = [
            models.Index(fields=["expense_id"]),
            models.Index(fields=["group_id"]),
            models.Index(fields=["user_id"]),
        ]


class DebtLedgerEntry(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group_id = models.UUIDField(db_index=True)
    source_expense_id = models.UUIDField(null=True, blank=True, db_index=True)
    source_expense_version = models.PositiveIntegerField(default=1)
    debtor_user_id = models.UUIDField(db_index=True)
    creditor_user_id = models.UUIDField(db_index=True)
    amount_minor = models.BigIntegerField(default=0)
    currency = models.CharField(
        max_length=3, choices=CurrencyChoices.choices, default=CurrencyChoices.IRR
    )
    entry_type = models.CharField(
        max_length=20, choices=DebtLedgerEntryTypeChoices.choices
    )
    status = models.CharField(
        max_length=10,
        choices=DebtLedgerStatusChoices.choices,
        default=DebtLedgerStatusChoices.ACTIVE,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    reversed_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = "settlement_debt_ledger_entries"
        indexes = [
            models.Index(fields=["group_id"]),
            models.Index(fields=["source_expense_id"]),
            models.Index(fields=["debtor_user_id"]),
            models.Index(fields=["creditor_user_id"]),
        ]


class GroupBalanceSnapshot(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group_id = models.UUIDField(db_index=True)
    user_id = models.UUIDField(db_index=True)
    currency = models.CharField(
        max_length=3, choices=CurrencyChoices.choices, default=CurrencyChoices.IRR
    )
    total_paid_minor = models.BigIntegerField(default=0)
    total_share_minor = models.BigIntegerField(default=0)
    total_settled_paid_minor = models.BigIntegerField(default=0)
    total_settled_received_minor = models.BigIntegerField(default=0)
    net_balance_minor = models.BigIntegerField(default=0)
    calculated_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "settlement_group_balance_snapshots"
        unique_together = (("group_id", "user_id", "currency"),)
        indexes = [models.Index(fields=["group_id"]), models.Index(fields=["user_id"])]


class ManualSettlement(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group_id = models.UUIDField(db_index=True)
    payer_user_id = models.UUIDField(db_index=True)
    receiver_user_id = models.UUIDField(db_index=True)
    amount_minor = models.BigIntegerField(default=0)
    currency = models.CharField(
        max_length=3, choices=CurrencyChoices.choices, default=CurrencyChoices.IRR
    )
    description = models.TextField(null=True, blank=True)
    status = models.CharField(
        max_length=30,
        choices=ManualSettlementStatusChoices.choices,
        default=ManualSettlementStatusChoices.PENDING_CONFIRMATION,
    )
    created_by_user_id = models.UUIDField()
    confirmed_by_user_id = models.UUIDField(null=True, blank=True)
    rejected_by_user_id = models.UUIDField(null=True, blank=True)
    cancelled_by_user_id = models.UUIDField(null=True, blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "settlement_manual_settlements"
        indexes = [
            models.Index(fields=["group_id"]),
            models.Index(fields=["payer_user_id"]),
            models.Index(fields=["receiver_user_id"]),
        ]


class ProcessedEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_id = models.UUIDField(unique=True, db_index=True)
    event_type = models.CharField(max_length=128)
    source_service = models.CharField(max_length=128)
    processed_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "settlement_processed_events"


class SettlementPlan(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group_id = models.UUIDField(db_index=True)
    currency = models.CharField(
        max_length=3, choices=CurrencyChoices.choices, default=CurrencyChoices.IRR
    )
    status = models.CharField(
        max_length=10,
        choices=SettlementPlanStatusChoices.choices,
        default=SettlementPlanStatusChoices.DRAFT,
    )
    generated_by_user_id = models.UUIDField()
    activated_by_user_id = models.UUIDField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    source_balance_calculated_at = models.DateTimeField()
    total_debt_minor = models.BigIntegerField(default=0)
    transaction_count = models.PositiveIntegerField(default=0)
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "settlement_settlement_plans"
        indexes = [
            models.Index(fields=["group_id"]),
            models.Index(fields=["status"]),
        ]


class SettlementPlanItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    settlement_plan_id = models.UUIDField(db_index=True)
    group_id = models.UUIDField(db_index=True)
    payer_user_id = models.UUIDField(db_index=True)
    receiver_user_id = models.UUIDField(db_index=True)
    amount_minor = models.BigIntegerField(default=0)
    currency = models.CharField(
        max_length=3, choices=CurrencyChoices.choices, default=CurrencyChoices.IRR
    )
    status = models.CharField(
        max_length=10,
        choices=SettlementPlanItemStatusChoices.choices,
        default=SettlementPlanItemStatusChoices.PENDING,
    )
    manual_settlement_id = models.UUIDField(null=True, blank=True)
    order_index = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    reported_at = models.DateTimeField(null=True, blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "settlement_settlement_plan_items"
        indexes = [
            models.Index(fields=["settlement_plan_id"]),
            models.Index(fields=["group_id"]),
            models.Index(fields=["payer_user_id"]),
            models.Index(fields=["receiver_user_id"]),
            models.Index(fields=["status"]),
        ]


class SettlementPlanEventLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    settlement_plan_id = models.UUIDField(db_index=True)
    settlement_plan_item_id = models.UUIDField(null=True, blank=True, db_index=True)
    actor_user_id = models.UUIDField(db_index=True)
    event_type = models.CharField(
        max_length=30, choices=SettlementPlanEventTypeChoices.choices
    )
    metadata = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "settlement_settlement_plan_event_logs"
        indexes = [
            models.Index(fields=["settlement_plan_id"]),
            models.Index(fields=["settlement_plan_item_id"]),
            models.Index(fields=["actor_user_id"]),
            models.Index(fields=["event_type"]),
        ]
