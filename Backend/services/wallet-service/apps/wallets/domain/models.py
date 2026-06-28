
from __future__ import annotations

import uuid

from django.db import models
from django.utils import timezone


class CurrencyChoices(models.TextChoices):
    IRR = "IRR", "Iranian Rial"


class WalletStatusChoices(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    INACTIVE = "INACTIVE", "Inactive"
    SUSPENDED = "SUSPENDED", "Suspended"


class WalletTransactionTypeChoices(models.TextChoices):
    TOP_UP = "TOP_UP", "Top Up"
    WITHDRAWAL = "WITHDRAWAL", "Withdrawal"
    TRANSFER_SENT = "TRANSFER_SENT", "Transfer Sent"
    TRANSFER_RECEIVED = "TRANSFER_RECEIVED", "Transfer Received"
    SETTLEMENT_PAYMENT = "SETTLEMENT_PAYMENT", "Settlement Payment"
    SETTLEMENT_RECEIVED = "SETTLEMENT_RECEIVED", "Settlement Received"
    REFUND = "REFUND", "Refund"
    ADJUSTMENT = "ADJUSTMENT", "Adjustment"


class WalletTransactionStatusChoices(models.TextChoices):
    PENDING = "PENDING", "Pending"
    PROCESSING = "PROCESSING", "Processing"
    COMPLETED = "COMPLETED", "Completed"
    FAILED = "FAILED", "Failed"
    CANCELLED = "CANCELLED", "Cancelled"


class WalletTransactionDirectionChoices(models.TextChoices):
    IN = "IN", "In"
    OUT = "OUT", "Out"


class LedgerEntryTypeChoices(models.TextChoices):
    AVAILABLE_DEBIT = "AVAILABLE_DEBIT", "Available Debit"
    AVAILABLE_CREDIT = "AVAILABLE_CREDIT", "Available Credit"
    RESERVED_DEBIT = "RESERVED_DEBIT", "Reserved Debit"
    RESERVED_CREDIT = "RESERVED_CREDIT", "Reserved Credit"


class WithdrawalStatusChoices(models.TextChoices):
    PENDING = "PENDING", "Pending"
    PROCESSING = "PROCESSING", "Processing"
    COMPLETED = "COMPLETED", "Completed"
    FAILED = "FAILED", "Failed"
    CANCELLED = "CANCELLED", "Cancelled"


class TopUpStatusChoices(models.TextChoices):
    PENDING = "PENDING", "Pending"
    PROCESSING = "PROCESSING", "Processing"
    COMPLETED = "COMPLETED", "Completed"
    FAILED = "FAILED", "Failed"
    CANCELLED = "CANCELLED", "Cancelled"


class PaymentProviderChoices(models.TextChoices):
    FAKE = "FAKE", "Fake Provider"


class PaymentPurposeChoices(models.TextChoices):
    WALLET_TOP_UP = "WALLET_TOP_UP", "Wallet Top Up"
    SETTLEMENT_PAYMENT = "SETTLEMENT_PAYMENT", "Settlement Payment"


class PaymentIntentStatusChoices(models.TextChoices):
    REDIRECT_REQUIRED = "REDIRECT_REQUIRED", "Redirect Required"
    CALLBACK_RECEIVED = "CALLBACK_RECEIVED", "Callback Received"
    PROCESSING = "PROCESSING", "Processing"
    SUCCEEDED = "SUCCEEDED", "Succeeded"
    FAILED = "FAILED", "Failed"
    RETRYABLE = "RETRYABLE", "Retryable"
    EXPIRED = "EXPIRED", "Expired"
    CANCELLED = "CANCELLED", "Cancelled"


class GatewayTransactionStatusChoices(models.TextChoices):
    CALLBACK_RECEIVED = "CALLBACK_RECEIVED", "Callback Received"
    VERIFYING = "VERIFYING", "Verifying"
    SUCCEEDED = "SUCCEEDED", "Succeeded"
    FAILED = "FAILED", "Failed"
    RETRYABLE = "RETRYABLE", "Retryable"


class SettlementItemStatusChoices(models.TextChoices):
    PENDING = "PENDING", "Pending"
    REPORTED = "REPORTED", "Reported"
    CONFIRMED = "CONFIRMED", "Confirmed"
    REJECTED = "REJECTED", "Rejected"
    CANCELLED = "CANCELLED", "Cancelled"


class SettlementPlanStatusChoices(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    ACTIVE = "ACTIVE", "Active"
    COMPLETED = "COMPLETED", "Completed"
    CANCELLED = "CANCELLED", "Cancelled"
    EXPIRED = "EXPIRED", "Expired"


class OutboxMessageStatusChoices(models.TextChoices):
    PENDING = "PENDING", "Pending"
    PUBLISHED = "PUBLISHED", "Published"
    FAILED = "FAILED", "Failed"


class InboxMessageStatusChoices(models.TextChoices):
    PROCESSED = "PROCESSED", "Processed"
    SKIPPED = "SKIPPED", "Skipped"
    FAILED = "FAILED", "Failed"


class UserProjection(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    identity_user_id = models.UUIDField(unique=True, db_index=True)
    email = models.CharField(max_length=254)
    art_name = models.CharField(max_length=255, null=True, blank=True)
    first_name = models.CharField(max_length=150, null=True, blank=True)
    last_name = models.CharField(max_length=150, null=True, blank=True)
    role = models.CharField(max_length=20, default="USER")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "wallet_user_projections"


class Wallet(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.UUIDField(db_index=True)
    currency = models.CharField(max_length=3, choices=CurrencyChoices.choices, default=CurrencyChoices.IRR)
    status = models.CharField(max_length=20, choices=WalletStatusChoices.choices, default=WalletStatusChoices.ACTIVE)
    available_balance_minor = models.BigIntegerField(default=0)
    reserved_balance_minor = models.BigIntegerField(default=0)
    total_inflow_minor = models.BigIntegerField(default=0)
    total_outflow_minor = models.BigIntegerField(default=0)
    last_ledger_recalculated_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "wallet_wallets"
        constraints = [
            models.UniqueConstraint(fields=["user_id", "currency"], name="wallet_unique_user_currency"),
        ]
        indexes = [
            models.Index(fields=["user_id", "status"]),
        ]


class WalletTransaction(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name="transactions")
    operation_id = models.UUIDField(default=uuid.uuid4, db_index=True)
    type = models.CharField(max_length=32, choices=WalletTransactionTypeChoices.choices)
    status = models.CharField(max_length=20, choices=WalletTransactionStatusChoices.choices, default=WalletTransactionStatusChoices.PENDING)
    direction = models.CharField(max_length=3, choices=WalletTransactionDirectionChoices.choices)
    amount_minor = models.BigIntegerField()
    currency = models.CharField(max_length=3, choices=CurrencyChoices.choices, default=CurrencyChoices.IRR)
    description = models.CharField(max_length=255, null=True, blank=True)
    reference_type = models.CharField(max_length=64, null=True, blank=True)
    reference_id = models.UUIDField(null=True, blank=True, db_index=True)
    idempotency_key = models.CharField(max_length=255, db_index=True)
    failure_reason = models.CharField(max_length=255, null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "wallet_transactions"
        constraints = [
            models.UniqueConstraint(fields=["wallet", "idempotency_key"], name="wallet_tx_unique_wallet_idempotency"),
        ]
        indexes = [
            models.Index(fields=["wallet", "status"]),
            models.Index(fields=["wallet", "type", "status"]),
            models.Index(fields=["wallet", "direction", "created_at"]),
            models.Index(fields=["reference_type", "reference_id"]),
        ]


class LedgerEntry(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name="ledger_entries")
    transaction = models.ForeignKey(WalletTransaction, on_delete=models.CASCADE, related_name="ledger_entries", null=True, blank=True)
    entry_type = models.CharField(max_length=32, choices=LedgerEntryTypeChoices.choices)
    amount_minor = models.BigIntegerField()
    currency = models.CharField(max_length=3, choices=CurrencyChoices.choices, default=CurrencyChoices.IRR)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "wallet_ledger_entries"
        indexes = [
            models.Index(fields=["wallet", "entry_type"]),
            models.Index(fields=["transaction"]),
        ]


class PaymentIntent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name="payment_intents")
    purpose = models.CharField(max_length=32, choices=PaymentPurposeChoices.choices, default=PaymentPurposeChoices.WALLET_TOP_UP)
    amount_minor = models.BigIntegerField()
    currency = models.CharField(max_length=3, choices=CurrencyChoices.choices, default=CurrencyChoices.IRR)
    provider = models.CharField(max_length=32, choices=PaymentProviderChoices.choices, default=PaymentProviderChoices.FAKE)
    idempotency_key = models.CharField(max_length=255, db_index=True)
    status = models.CharField(max_length=32, choices=PaymentIntentStatusChoices.choices, default=PaymentIntentStatusChoices.REDIRECT_REQUIRED)
    payment_url = models.URLField(max_length=500)
    expires_at = models.DateTimeField()
    last_callback_at = models.DateTimeField(null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    provider_reference = models.CharField(max_length=255, null=True, blank=True)
    failure_reason = models.CharField(max_length=255, null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "wallet_payment_intents"
        constraints = [
            models.UniqueConstraint(fields=["wallet", "idempotency_key"], name="wallet_payment_intent_unique_wallet_idempotency"),
        ]
        indexes = [
            models.Index(fields=["wallet", "status"]),
            models.Index(fields=["provider", "status"]),
            models.Index(fields=["expires_at"]),
        ]


class GatewayTransaction(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment_intent = models.OneToOneField(PaymentIntent, on_delete=models.CASCADE, related_name="gateway_transaction")
    provider = models.CharField(max_length=32, choices=PaymentProviderChoices.choices, default=PaymentProviderChoices.FAKE)
    provider_reference = models.CharField(max_length=255, unique=True, null=True, blank=True)
    status = models.CharField(max_length=32, choices=GatewayTransactionStatusChoices.choices, default=GatewayTransactionStatusChoices.CALLBACK_RECEIVED)
    callback_count = models.PositiveIntegerField(default=0)
    provider_amount_minor = models.BigIntegerField(null=True, blank=True)
    provider_currency = models.CharField(max_length=3, choices=CurrencyChoices.choices, default=CurrencyChoices.IRR)
    provider_status = models.CharField(max_length=64, null=True, blank=True)
    last_callback_payload = models.JSONField(default=dict, blank=True)
    last_verify_response = models.JSONField(default=dict, blank=True)
    last_callback_at = models.DateTimeField(null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    verification_attempts = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "wallet_gateway_transactions"
        indexes = [
            models.Index(fields=["provider", "status"]),
            models.Index(fields=["provider", "provider_reference"]),
        ]


class Withdrawal(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name="withdrawals")
    amount_minor = models.BigIntegerField()
    currency = models.CharField(max_length=3, choices=CurrencyChoices.choices, default=CurrencyChoices.IRR)
    payment_method_id = models.UUIDField()
    payment_method_masked = models.CharField(max_length=32, null=True, blank=True)
    status = models.CharField(max_length=20, choices=WithdrawalStatusChoices.choices, default=WithdrawalStatusChoices.PENDING)
    idempotency_key = models.CharField(max_length=255, db_index=True)
    withdrawal_transaction = models.OneToOneField(WalletTransaction, on_delete=models.PROTECT, related_name="withdrawal_record")
    cancel_transaction = models.OneToOneField(WalletTransaction, on_delete=models.PROTECT, related_name="withdrawal_cancel_record", null=True, blank=True)
    failure_reason = models.CharField(max_length=255, null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "wallet_withdrawals"
        constraints = [
            models.UniqueConstraint(fields=["wallet", "idempotency_key"], name="wallet_withdrawal_unique_wallet_idempotency"),
        ]
        indexes = [
            models.Index(fields=["wallet", "status"]),
        ]


class TopUp(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name="topups")
    payment_intent = models.OneToOneField(PaymentIntent, on_delete=models.PROTECT, related_name="top_up", null=True, blank=True)
    gateway_transaction = models.OneToOneField(GatewayTransaction, on_delete=models.PROTECT, related_name="top_up", null=True, blank=True)
    wallet_transaction = models.OneToOneField(WalletTransaction, on_delete=models.PROTECT, related_name="top_up_record", null=True, blank=True)
    amount_minor = models.BigIntegerField()
    currency = models.CharField(max_length=3, choices=CurrencyChoices.choices, default=CurrencyChoices.IRR)
    status = models.CharField(max_length=20, choices=TopUpStatusChoices.choices, default=TopUpStatusChoices.PENDING)
    provider = models.CharField(max_length=64, choices=PaymentProviderChoices.choices, default=PaymentProviderChoices.FAKE)
    provider_reference = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    idempotency_key = models.CharField(max_length=255, db_index=True)
    failure_reason = models.CharField(max_length=255, null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "wallet_topups"
        constraints = [
            models.UniqueConstraint(fields=["wallet", "idempotency_key"], name="wallet_topup_unique_wallet_idempotency"),
        ]
        indexes = [
            models.Index(fields=["wallet", "status"]),
        ]


class PaymentCallbackLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.CharField(max_length=32, choices=PaymentProviderChoices.choices, default=PaymentProviderChoices.FAKE)
    payment_intent = models.ForeignKey(PaymentIntent, on_delete=models.SET_NULL, null=True, blank=True, related_name="callback_logs")
    provider_reference = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    method = models.CharField(max_length=8)
    payload = models.JSONField(default=dict)
    received_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "wallet_payment_callback_logs"
        indexes = [
            models.Index(fields=["provider", "provider_reference"]),
            models.Index(fields=["payment_intent", "received_at"]),
        ]


class SettlementItemProjection(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    item_id = models.UUIDField(unique=True, db_index=True)
    plan_id = models.UUIDField(db_index=True)
    group_id = models.UUIDField(db_index=True)
    payer_user_id = models.UUIDField(db_index=True)
    payee_user_id = models.UUIDField(db_index=True)
    amount_minor = models.BigIntegerField()
    currency = models.CharField(max_length=3, choices=CurrencyChoices.choices, default=CurrencyChoices.IRR)
    item_status = models.CharField(max_length=20, choices=SettlementItemStatusChoices.choices, default=SettlementItemStatusChoices.PENDING)
    plan_status = models.CharField(max_length=20, choices=SettlementPlanStatusChoices.choices, default=SettlementPlanStatusChoices.DRAFT)
    wallet_payment_transaction_id = models.UUIDField(null=True, blank=True, unique=True)
    wallet_payment_completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField()

    class Meta:
        db_table = "wallet_settlement_item_projections"
        indexes = [
            models.Index(fields=["payer_user_id", "plan_status", "item_status"]),
            models.Index(fields=["payee_user_id", "plan_status", "item_status"]),
            models.Index(fields=["group_id", "plan_status"]),
        ]


class OutboxMessage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_id = models.UUIDField(unique=True, db_index=True, default=uuid.uuid4)
    source_service = models.CharField(max_length=128, default="wallet-service")
    aggregate_type = models.CharField(max_length=64)
    aggregate_id = models.UUIDField(null=True, blank=True, db_index=True)
    event_type = models.CharField(max_length=128)
    event_version = models.PositiveIntegerField(default=1)
    routing_key = models.CharField(max_length=128)
    exchange = models.CharField(max_length=128, default="hamdong.wallet")
    correlation_id = models.UUIDField(null=True, blank=True, db_index=True)
    causation_id = models.UUIDField(null=True, blank=True, db_index=True)
    payload = models.JSONField(default=dict)
    status = models.CharField(max_length=20, choices=OutboxMessageStatusChoices.choices, default=OutboxMessageStatusChoices.PENDING)
    retry_count = models.PositiveIntegerField(default=0)
    available_at = models.DateTimeField(default=timezone.now, db_index=True)
    published_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "wallet_outbox_messages"
        indexes = [
            models.Index(fields=["status", "available_at"]),
            models.Index(fields=["aggregate_type", "aggregate_id"]),
            models.Index(fields=["routing_key"]),
        ]


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
        db_table = "wallet_inbox_messages"
        indexes = [
            models.Index(fields=["event_type"]),
            models.Index(fields=["routing_key"]),
        ]
