from rest_framework import serializers
from django.conf import settings


class BalanceItemSerializer(serializers.Serializer):
    user_id = serializers.UUIDField()
    art_name = serializers.CharField(allow_null=True, required=False)
    email = serializers.CharField(required=False)
    net_balance_minor = serializers.IntegerField()
    status = serializers.CharField()


class GroupBalancesResponseSerializer(serializers.Serializer):
    group_id = serializers.UUIDField()
    currency = serializers.CharField()
    balances = BalanceItemSerializer(many=True)
    calculated_at = serializers.DateTimeField()


class MyBalanceResponseSerializer(serializers.Serializer):
    group_id = serializers.UUIDField()
    user_id = serializers.UUIDField()
    currency = serializers.CharField()
    net_balance_minor = serializers.IntegerField()
    status = serializers.CharField()


class DebtItemSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    source_expense_id = serializers.UUIDField(required=False, allow_null=True)
    debtor_user_id = serializers.UUIDField()
    creditor_user_id = serializers.UUIDField()
    amount_minor = serializers.IntegerField()
    status = serializers.CharField()
    entry_type = serializers.CharField()


class GroupDebtsResponseSerializer(serializers.Serializer):
    group_id = serializers.UUIDField()
    currency = serializers.CharField()
    debts = DebtItemSerializer(many=True)


class ManualSettlementCreateSerializer(serializers.Serializer):
    receiver_user_id = serializers.UUIDField()
    amount_minor = serializers.IntegerField()
    currency = serializers.CharField(default="IRR")
    description = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )

    def validate_amount_minor(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "Settlement amount must be greater than zero."
            )
        if value > getattr(settings, "MAX_SETTLEMENT_AMOUNT_MINOR", 100000000000):
            raise serializers.ValidationError(
                "Settlement amount exceeds the allowed maximum."
            )
        return value

    def validate_currency(self, value):
        if value != "IRR":
            raise serializers.ValidationError(
                "Only IRR currency is supported in this phase."
            )
        return value


class ManualSettlementItemSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    group_id = serializers.UUIDField()
    payer_user_id = serializers.UUIDField()
    receiver_user_id = serializers.UUIDField()
    amount_minor = serializers.IntegerField()
    currency = serializers.CharField()
    status = serializers.CharField()
    description = serializers.CharField(required=False, allow_null=True)
    created_at = serializers.DateTimeField()


class ManualSettlementListResponseSerializer(serializers.Serializer):
    group_id = serializers.UUIDField()
    settlements = ManualSettlementItemSerializer(many=True)


class MessageSerializer(serializers.Serializer):
    message = serializers.CharField()


class SettlementRejectSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class SettlementPlanItemSummarySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    payer_user_id = serializers.UUIDField()
    payer_art_name = serializers.CharField(allow_null=True, required=False)
    receiver_user_id = serializers.UUIDField()
    receiver_art_name = serializers.CharField(allow_null=True, required=False)
    amount_minor = serializers.IntegerField()
    status = serializers.CharField()
    order_index = serializers.IntegerField()


class SettlementPlanDetailSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    group_id = serializers.UUIDField()
    currency = serializers.CharField()
    status = serializers.CharField()
    total_debt_minor = serializers.IntegerField()
    transaction_count = serializers.IntegerField()
    source_balance_calculated_at = serializers.DateTimeField(required=False)
    created_at = serializers.DateTimeField(required=False)
    updated_at = serializers.DateTimeField(required=False)
    items = SettlementPlanItemSummarySerializer(many=True)


class SettlementPlanGenerateSerializer(serializers.Serializer):
    pass


class SettlementPlanReportPaidSerializer(serializers.Serializer):
    description = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )


class SettlementPlanRejectItemSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class MessageWithManualSettlementSerializer(serializers.Serializer):
    message = serializers.CharField()
    manual_settlement_id = serializers.UUIDField()
