import uuid
from decimal import Decimal
from django.db import models
from django.utils import timezone


class UserProjection(models.Model):
    """User projection for expense-service. Consumed from identity-service events."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    identity_user_id = models.UUIDField(unique=True)
    email = models.CharField(max_length=254)
    art_name = models.CharField(max_length=255, null=True, blank=True)
    first_name = models.CharField(max_length=150, null=True, blank=True)
    last_name = models.CharField(max_length=150, null=True, blank=True)

    ROLE_USER = "USER"
    ROLE_ADMIN = "ADMIN"
    ROLE_CHOICES = ((ROLE_USER, ROLE_USER), (ROLE_ADMIN, ROLE_ADMIN))

    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=ROLE_USER)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "expenses_userprojection"



class BankCardProjection(models.Model):
    """Safe bank card projection consumed from identity-service events."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    card_id = models.UUIDField(unique=True)
    user_id = models.UUIDField(db_index=True)
    holder_name = models.CharField(max_length=150)
    bank_name = models.CharField(max_length=100, null=True, blank=True)
    card_number_last4 = models.CharField(max_length=4)
    masked_card_number = models.CharField(max_length=24)
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "expenses_bankcardprojection"
        indexes = [models.Index(fields=["user_id", "is_active"]), models.Index(fields=["user_id", "is_default"])]



class GroupProjection(models.Model):
    """Group projection for expense-service. Consumed from group-service events."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group_id = models.UUIDField(unique=True)
    title = models.CharField(max_length=255)

    TYPE_EVENT = "EVENT"
    TYPE_TRIP = "TRIP"
    TYPE_GENERAL = "GENERAL"
    GROUP_TYPE_CHOICES = ((TYPE_EVENT, TYPE_EVENT), (TYPE_TRIP, TYPE_TRIP), (TYPE_GENERAL, TYPE_GENERAL))

    group_type = models.CharField(max_length=20, choices=GROUP_TYPE_CHOICES, default=TYPE_GENERAL)

    STATUS_ACTIVE = "ACTIVE"
    STATUS_ARCHIVED = "ARCHIVED"
    STATUS_DELETED = "DELETED"
    STATUS_CHOICES = ((STATUS_ACTIVE, STATUS_ACTIVE), (STATUS_ARCHIVED, STATUS_ARCHIVED), (STATUS_DELETED, STATUS_DELETED))

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    created_by_user_id = models.UUIDField()
    member_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "expenses_groupprojection"


class GroupMemberProjection(models.Model):
    """Group member projection. Only ACTIVE members can create/participate in expenses."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group_id = models.UUIDField(db_index=True)
    user_id = models.UUIDField(db_index=True)
    email = models.CharField(max_length=254)
    art_name_snapshot = models.CharField(max_length=255, null=True, blank=True)

    ROLE_OWNER = "OWNER"
    ROLE_ADMIN = "ADMIN"
    ROLE_MEMBER = "MEMBER"
    MEMBER_ROLE_CHOICES = ((ROLE_OWNER, ROLE_OWNER), (ROLE_ADMIN, ROLE_ADMIN), (ROLE_MEMBER, ROLE_MEMBER))

    role = models.CharField(max_length=10, choices=MEMBER_ROLE_CHOICES, default=ROLE_MEMBER)

    STATUS_ACTIVE = "ACTIVE"
    STATUS_LEFT = "LEFT"
    STATUS_REMOVED = "REMOVED"
    MEMBER_STATUS_CHOICES = ((STATUS_ACTIVE, STATUS_ACTIVE), (STATUS_LEFT, STATUS_LEFT), (STATUS_REMOVED, STATUS_REMOVED))

    status = models.CharField(max_length=10, choices=MEMBER_STATUS_CHOICES, default=STATUS_ACTIVE)
    joined_at = models.DateTimeField(null=True, blank=True)
    left_at = models.DateTimeField(null=True, blank=True)
    removed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "expenses_groupmemberprojection"
        indexes = [models.Index(fields=["group_id"]), models.Index(fields=["user_id"])]


class Expense(models.Model):
    """
    Expense model with financial amounts stored as integer minor units (no floats).
    
    Financial invariant:
    total_amount_minor = base_amount_minor + tax_amount_minor + service_fee_amount_minor
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group_id = models.UUIDField(db_index=True)
    created_by_user_id = models.UUIDField()
    payer_user_id = models.UUIDField()
    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    currency = models.CharField(max_length=10, default="IRR")

    # amounts stored as minor units (integers, no floats)
    base_amount_minor = models.BigIntegerField()

    TAX_NONE = "NONE"
    TAX_PERCENTAGE = "PERCENTAGE"
    TAX_FIXED = "FIXED"
    TAX_TYPE_CHOICES = ((TAX_NONE, TAX_NONE), (TAX_PERCENTAGE, TAX_PERCENTAGE), (TAX_FIXED, TAX_FIXED))

    tax_type = models.CharField(max_length=20, choices=TAX_TYPE_CHOICES, default=TAX_NONE)
    tax_percentage = models.DecimalField(max_digits=7, decimal_places=4, null=True, blank=True)
    tax_amount_minor = models.BigIntegerField(default=0)

    SERVICE_NONE = "NONE"
    SERVICE_PERCENTAGE = "PERCENTAGE"
    SERVICE_FIXED = "FIXED"
    SERVICE_TYPE_CHOICES = ((SERVICE_NONE, SERVICE_NONE), (SERVICE_PERCENTAGE, SERVICE_PERCENTAGE), (SERVICE_FIXED, SERVICE_FIXED))

    service_fee_type = models.CharField(max_length=20, choices=SERVICE_TYPE_CHOICES, default=SERVICE_NONE)
    service_fee_percentage = models.DecimalField(max_digits=7, decimal_places=4, null=True, blank=True)
    service_fee_amount_minor = models.BigIntegerField(default=0)

    total_amount_minor = models.BigIntegerField()

    SPLIT_EQUAL = "EQUAL"
    SPLIT_CUSTOM = "CUSTOM_AMOUNT"
    SPLIT_METHOD_CHOICES = ((SPLIT_EQUAL, SPLIT_EQUAL), (SPLIT_CUSTOM, SPLIT_CUSTOM))

    split_method = models.CharField(max_length=20, choices=SPLIT_METHOD_CHOICES, default=SPLIT_EQUAL)
    receipt_file_id = models.UUIDField(null=True, blank=True)
    receipt_url = models.CharField(max_length=1024, null=True, blank=True)

    STATUS_ACTIVE = "ACTIVE"
    STATUS_UPDATED = "UPDATED"
    STATUS_DELETED = "DELETED"
    EXPENSE_STATUS_CHOICES = ((STATUS_ACTIVE, STATUS_ACTIVE), (STATUS_UPDATED, STATUS_UPDATED), (STATUS_DELETED, STATUS_DELETED))

    status = models.CharField(max_length=10, choices=EXPENSE_STATUS_CHOICES, default=STATUS_ACTIVE)
    expense_date = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    version = models.IntegerField(default=1)

    class Meta:
        db_table = "expenses_expense"



class ExpensePaymentOption(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    expense = models.ForeignKey("Expense", related_name="payment_options", on_delete=models.CASCADE)
    bank_card_id = models.UUIDField(db_index=True)
    holder_name = models.CharField(max_length=150)
    bank_name = models.CharField(max_length=100, null=True, blank=True)
    card_number_last4 = models.CharField(max_length=4)
    masked_card_number = models.CharField(max_length=24)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "expenses_expensepaymentoption"
        constraints = [
            models.UniqueConstraint(fields=["expense", "bank_card_id"], name="uniq_expense_payment_option")
        ]



class ExpenseParticipant(models.Model):
    """
    Expense participant with shares distributed proportionally.
    
    Financial invariant:
    total_share_minor = base_share_minor + tax_share_minor + service_fee_share_minor
    
    And across all participants:
    sum(total_share_minor) == expense.total_amount_minor
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    expense = models.ForeignKey("Expense", related_name="participants", on_delete=models.CASCADE)
    user_id = models.UUIDField(db_index=True)
    email = models.CharField(max_length=254)
    art_name_snapshot = models.CharField(max_length=255, null=True, blank=True)
    base_share_minor = models.BigIntegerField()
    tax_share_minor = models.BigIntegerField(default=0)
    service_fee_share_minor = models.BigIntegerField(default=0)
    total_share_minor = models.BigIntegerField()
    is_included = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "expenses_expenseparticipant"
        unique_together = (("expense", "user_id"),)


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
        db_table = "expenses_outbox_messages"
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
        db_table = "expenses_inbox_messages"
        indexes = [models.Index(fields=["event_type"]), models.Index(fields=["routing_key"])]

