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


class MySettlementsQuerySerializer(serializers.Serializer):
    direction = serializers.ChoiceField(choices=["PAY", "RECEIVE"], required=False)
    status = serializers.ChoiceField(
        choices=[
            "PENDING",
            "REPORTED",
            "CONFIRMED",
            "REJECTED",
            "CANCELLED",
            "PENDING_CONFIRMATION",
        ],
        required=False,
    )    
    action_required = serializers.BooleanField(required=False)
    group_id = serializers.UUIDField(required=False)
    cursor = serializers.CharField(required=False)
    page_size = serializers.IntegerField(required=False, min_value=1, max_value=100)


class SettlementFeedGroupSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    title = serializers.CharField()


class SettlementFeedCounterpartySerializer(serializers.Serializer):
    user_id = serializers.UUIDField()
    art_name = serializers.CharField(allow_null=True, required=False)


class SettlementFeedItemSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    source_type = serializers.CharField()
    source_id = serializers.UUIDField()
    group = SettlementFeedGroupSerializer()
    counterparty = SettlementFeedCounterpartySerializer()
    direction = serializers.ChoiceField(choices=["PAY", "RECEIVE"])
    amount_minor = serializers.IntegerField()
    currency = serializers.CharField()
    status = serializers.CharField()
    action_required = serializers.CharField(allow_null=True, required=False)
    allowed_actions = serializers.ListField(child=serializers.CharField())
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class MySettlementsResponseSerializer(serializers.Serializer):
    results = SettlementFeedItemSerializer(many=True)
    next_cursor = serializers.CharField(allow_null=True, required=False)


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
    payment_method = serializers.CharField(required=False, allow_blank=False)
    paid_to_bank_card_id = serializers.UUIDField(required=False, allow_null=True)
    amount_minor = serializers.IntegerField(required=False)
    paid_at = serializers.DateTimeField(required=False, allow_null=True)
    note = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=500)
    tracking_code = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=64)
    receipt_file_id = serializers.UUIDField(required=False, allow_null=True)


class SettlementPlanRejectItemSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class MessageWithManualSettlementSerializer(serializers.Serializer):
    message = serializers.CharField()
    manual_settlement_id = serializers.UUIDField()
    settlement_item_id = serializers.UUIDField(required=False)
    status = serializers.CharField(required=False)
    payment_method = serializers.CharField(required=False, allow_null=True)
    paid_to_bank_card = serializers.DictField(required=False)
    amount_minor = serializers.IntegerField(required=False)
    currency = serializers.CharField(required=False)
    reported_at = serializers.DateTimeField(required=False, allow_null=True)


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



class SettlementPaymentOptionCardSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    type = serializers.CharField()
    card_number = serializers.CharField(required=False, allow_null=True)
    masked_card_number = serializers.CharField()
    card_number_last4 = serializers.CharField()
    bank_name = serializers.CharField(allow_null=True)
    holder_name = serializers.CharField()
    is_default = serializers.BooleanField()


class SettlementPaymentOptionsResponseSerializer(serializers.Serializer):
    settlement_item_id = serializers.UUIDField()
    group = serializers.DictField(required=False)
    payer = serializers.DictField(required=False)
    payee = serializers.DictField(required=False)
    amount_minor = serializers.IntegerField()
    currency = serializers.CharField()
    status = serializers.CharField()
    payment_options = SettlementPaymentOptionCardSerializer(many=True)
    message = serializers.CharField(required=False)
