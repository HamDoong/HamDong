
from __future__ import annotations

from rest_framework import serializers


class FlexibleDateTimeField(serializers.DateTimeField):
    def to_internal_value(self, value):
        if isinstance(value, str):
            value = value.replace(" ", "+")
        return super().to_internal_value(value)


TRANSACTION_TYPES = [
    "TOP_UP",
    "WITHDRAWAL",
    "TRANSFER_SENT",
    "TRANSFER_RECEIVED",
    "SETTLEMENT_PAYMENT",
    "SETTLEMENT_RECEIVED",
    "REFUND",
    "ADJUSTMENT",
]
TRANSACTION_STATUSES = [
    "PENDING",
    "PROCESSING",
    "COMPLETED",
    "FAILED",
    "CANCELLED",
]


class WalletSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    currency = serializers.CharField()
    status = serializers.CharField()
    available_balance_minor = serializers.IntegerField()
    reserved_balance_minor = serializers.IntegerField()
    total_inflow_minor = serializers.IntegerField()
    total_outflow_minor = serializers.IntegerField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class WalletTransactionItemSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    type = serializers.ChoiceField(choices=TRANSACTION_TYPES)
    status = serializers.ChoiceField(choices=TRANSACTION_STATUSES)
    direction = serializers.ChoiceField(choices=["IN", "OUT"])
    amount_minor = serializers.IntegerField()
    currency = serializers.CharField()
    description = serializers.CharField(allow_null=True, required=False)
    reference_type = serializers.CharField(allow_null=True, required=False)
    reference_id = serializers.UUIDField(allow_null=True, required=False)
    created_at = serializers.DateTimeField()
    completed_at = serializers.DateTimeField(allow_null=True, required=False)


class WalletTransactionListQuerySerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=TRANSACTION_TYPES, required=False)
    status = serializers.ChoiceField(choices=TRANSACTION_STATUSES, required=False)
    from_at = FlexibleDateTimeField(required=False)
    to = FlexibleDateTimeField(required=False)
    cursor = serializers.CharField(required=False)
    page_size = serializers.IntegerField(required=False, min_value=1, max_value=100)


class WalletTransactionListResponseSerializer(serializers.Serializer):
    results = WalletTransactionItemSerializer(many=True)
    next_cursor = serializers.CharField(allow_null=True, required=False)


class WalletSettlementPayRequestSerializer(serializers.Serializer):
    idempotency_key = serializers.CharField(max_length=255)

    def validate_idempotency_key(self, value):
        if not value.strip():
            raise serializers.ValidationError("This field may not be blank.")
        return value.strip()


class WalletSettlementPayResponseSerializer(serializers.Serializer):
    transaction_id = serializers.UUIDField()
    settlement_plan_item_id = serializers.UUIDField()
    status = serializers.CharField()
    amount_minor = serializers.IntegerField()
    currency = serializers.CharField()
    paid_at = serializers.DateTimeField()


class CounterpartySerializer(serializers.Serializer):
    user_id = serializers.UUIDField()
    art_name = serializers.CharField(allow_null=True, required=False)


class WalletSummarySettlementItemSerializer(serializers.Serializer):
    settlement_plan_item_id = serializers.UUIDField()
    plan_id = serializers.UUIDField()
    group_id = serializers.UUIDField()
    counterparty = CounterpartySerializer()
    amount_minor = serializers.IntegerField()
    currency = serializers.CharField()
    status = serializers.CharField()
    updated_at = serializers.DateTimeField()


class WithdrawalCreateSerializer(serializers.Serializer):
    amount_minor = serializers.IntegerField()
    currency = serializers.CharField()
    payment_method_id = serializers.UUIDField()
    idempotency_key = serializers.CharField(max_length=255)

    def validate_amount_minor(self, value):
        if int(value) <= 0:
            raise serializers.ValidationError("Amount must be greater than zero.")
        return int(value)

    def validate_currency(self, value):
        if value != "IRR":
            raise serializers.ValidationError("Only IRR currency is supported in this phase.")
        return value

    def validate_idempotency_key(self, value):
        if not value.strip():
            raise serializers.ValidationError("This field may not be blank.")
        return value.strip()


class WithdrawalItemSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    amount_minor = serializers.IntegerField()
    currency = serializers.CharField()
    payment_method_id = serializers.UUIDField()
    payment_method_masked = serializers.CharField(allow_null=True, required=False)
    status = serializers.ChoiceField(choices=["PENDING", "PROCESSING", "COMPLETED", "FAILED", "CANCELLED"])
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    completed_at = serializers.DateTimeField(allow_null=True, required=False)
    cancelled_at = serializers.DateTimeField(allow_null=True, required=False)
    failed_at = serializers.DateTimeField(allow_null=True, required=False)


class WithdrawalListResponseSerializer(serializers.Serializer):
    results = WithdrawalItemSerializer(many=True)


class WalletSummaryResponseSerializer(serializers.Serializer):
    wallet = WalletSerializer()
    pending_receivables = WalletSummarySettlementItemSerializer(many=True)
    pending_payables = WalletSummarySettlementItemSerializer(many=True)
    recent_transactions = WalletTransactionItemSerializer(many=True)
    pending_withdrawals = WithdrawalItemSerializer(many=True)
    generated_at = serializers.DateTimeField()


class MessageSerializer(serializers.Serializer):
    message = serializers.CharField()
