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


class ReminderSettingsSerializer(serializers.Serializer):
    group_id = serializers.UUIDField()
    is_enabled = serializers.BooleanField()
    first_reminder_after_hours = serializers.IntegerField()
    repeat_interval_hours = serializers.IntegerField()
    maximum_reminders = serializers.IntegerField()
    send_in_app = serializers.BooleanField()
    send_email = serializers.BooleanField()
    created_at = serializers.DateTimeField(allow_null=True)
    updated_at = serializers.DateTimeField(allow_null=True)


class ReminderSettingsPatchSerializer(serializers.Serializer):
    is_enabled = serializers.BooleanField(required=False)
    first_reminder_after_hours = serializers.IntegerField(required=False)
    repeat_interval_hours = serializers.IntegerField(required=False)
    maximum_reminders = serializers.IntegerField(required=False)
    send_in_app = serializers.BooleanField(required=False)
    send_email = serializers.BooleanField(required=False)


class ReminderHistoryItemSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    group_id = serializers.UUIDField()
    recipient_user_id = serializers.UUIDField()
    settlement_plan_item_id = serializers.UUIDField()
    sequence_number = serializers.IntegerField()
    source = serializers.CharField()
    channels = serializers.ListField(child=serializers.CharField())
    status = serializers.CharField()
    scheduled_at = serializers.DateTimeField(allow_null=True)
    requested_at = serializers.DateTimeField(allow_null=True)
    sent_at = serializers.DateTimeField(allow_null=True)
    last_error = serializers.CharField(allow_null=True)


class ReminderHistoryListSerializer(serializers.Serializer):
    results = ReminderHistoryItemSerializer(many=True)
    next_cursor = serializers.CharField(allow_null=True, required=False)


class ReminderDetailSerializer(ReminderHistoryItemSerializer):
    creditor_user_id = serializers.UUIDField()
    settlement_plan_id = serializers.UUIDField()
    item_reference = serializers.UUIDField()
    delivery_summary = serializers.JSONField()


class GroupRunReminderResponseSerializer(serializers.Serializer):
    eligible_count = serializers.IntegerField()
    created_count = serializers.IntegerField()
    skipped_count = serializers.IntegerField()
    skip_reasons = serializers.JSONField(required=False)


class GroupRunReminderRequestSerializer(serializers.Serializer):
    dry_run = serializers.BooleanField(required=False, default=False)


class ManualReminderSendSerializer(serializers.Serializer):
    send_in_app = serializers.BooleanField(required=False)
    send_email = serializers.BooleanField(required=False)


class ManualReminderSendResponseSerializer(serializers.Serializer):
    reminder_id = serializers.UUIDField()
    status = serializers.CharField()
    channels = serializers.ListField(child=serializers.CharField())
