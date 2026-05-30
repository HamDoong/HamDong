import uuid
from decimal import Decimal
from django.db import models
from django.utils import timezone


class UserProjection(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    identity_user_id = models.UUIDField(unique=True)
    phone_number = models.CharField(max_length=32)
    display_name = models.CharField(max_length=255, null=True, blank=True)
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


class GroupProjection(models.Model):
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
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group_id = models.UUIDField(db_index=True)
    user_id = models.UUIDField(db_index=True)
    phone_number = models.CharField(max_length=32)
    display_name_snapshot = models.CharField(max_length=255, null=True, blank=True)

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
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group_id = models.UUIDField(db_index=True)
    created_by_user_id = models.UUIDField()
    payer_user_id = models.UUIDField()
    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    currency = models.CharField(max_length=10, default="IRR")

    # amounts stored as minor units (integers)
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


class ExpenseParticipant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    expense = models.ForeignKey("Expense", related_name="participants", on_delete=models.CASCADE)
    user_id = models.UUIDField(db_index=True)
    phone_number = models.CharField(max_length=32)
    display_name_snapshot = models.CharField(max_length=255, null=True, blank=True)
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
import uuid
from django.db import models


class UserProjection(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    identity_user_id = models.UUIDField(unique=True)
    phone_number = models.CharField(max_length=32)
    display_name = models.CharField(max_length=255, null=True, blank=True)
    first_name = models.CharField(max_length=255, null=True, blank=True)
    last_name = models.CharField(max_length=255, null=True, blank=True)
    role = models.CharField(max_length=32, default="USER")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "expenses_user_projections"


class GroupProjection(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group_id = models.UUIDField(unique=True)
    title = models.CharField(max_length=255)
    group_type = models.CharField(max_length=32)
    status = models.CharField(max_length=32, default="ACTIVE")
    created_by_user_id = models.UUIDField()
    member_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "expenses_group_projections"


class GroupMemberProjection(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group_id = models.UUIDField()
    user_id = models.UUIDField()
    phone_number = models.CharField(max_length=32)
    display_name_snapshot = models.CharField(max_length=255, null=True, blank=True)
    role = models.CharField(max_length=16)
    status = models.CharField(max_length=16, default="ACTIVE")
    joined_at = models.DateTimeField(null=True, blank=True)
    left_at = models.DateTimeField(null=True, blank=True)
    removed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "expenses_group_member_projections"


class Expense(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group_id = models.UUIDField()
    created_by_user_id = models.UUIDField()
    payer_user_id = models.UUIDField()
    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    currency = models.CharField(max_length=8, default="IRR")
    base_amount_minor = models.BigIntegerField()
    tax_type = models.CharField(max_length=32, default="NONE")
    tax_percentage = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    tax_amount_minor = models.BigIntegerField(default=0)
    service_fee_type = models.CharField(max_length=32, default="NONE")
    service_fee_percentage = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    service_fee_amount_minor = models.BigIntegerField(default=0)
    total_amount_minor = models.BigIntegerField()
    split_method = models.CharField(max_length=32)
    receipt_file_id = models.UUIDField(null=True, blank=True)
    receipt_url = models.CharField(max_length=1024, null=True, blank=True)
    status = models.CharField(max_length=16, default="ACTIVE")
    expense_date = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = "expenses"


class ExpenseParticipant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    expense = models.ForeignKey(Expense, on_delete=models.CASCADE, related_name="participants")
    user_id = models.UUIDField()
    phone_number = models.CharField(max_length=32)
    display_name_snapshot = models.CharField(max_length=255, null=True, blank=True)
    base_share_minor = models.BigIntegerField()
    tax_share_minor = models.BigIntegerField(default=0)
    service_fee_share_minor = models.BigIntegerField(default=0)
    total_share_minor = models.BigIntegerField()
    is_included = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "expense_participants"
from django.db import models


class PlaceholderModel(models.Model):
    """Placeholder model to reserve the domain layer."""

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True
