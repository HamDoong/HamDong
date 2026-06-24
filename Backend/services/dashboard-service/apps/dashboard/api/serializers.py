from rest_framework import serializers

from apps.dashboard.application.dashboard_service import (
    ACTION_PRIORITY_CHOICES,
    ACTION_TYPE_CHOICES,
    ACTIVITY_TYPE_CHOICES,
)


class ErrorResponseSerializer(serializers.Serializer):
    error = serializers.DictField()


class MessageSerializer(serializers.Serializer):
    message = serializers.CharField()


class DashboardSummaryQuerySerializer(serializers.Serializer):
    currency = serializers.CharField(required=False, max_length=8)


class FinancialSummarySerializer(serializers.Serializer):
    currency = serializers.CharField()
    total_receivable_minor = serializers.IntegerField()
    total_payable_minor = serializers.IntegerField()
    net_balance_minor = serializers.IntegerField()


class DashboardSummaryResponseSerializer(serializers.Serializer):
    financials = FinancialSummarySerializer(many=True)
    active_groups_count = serializers.IntegerField()
    pending_settlements_count = serializers.IntegerField()
    action_items_count = serializers.IntegerField()
    important_unread_notifications_count = serializers.IntegerField()
    generated_at = serializers.DateTimeField()


class DashboardActionReferenceSerializer(serializers.Serializer):
    key = serializers.CharField()
    method = serializers.CharField()
    path = serializers.CharField()


class DashboardGroupSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    title = serializers.CharField()


class DashboardActionSourceSerializer(serializers.Serializer):
    service = serializers.CharField()
    type = serializers.CharField()
    id = serializers.CharField()


class DashboardActionItemSerializer(serializers.Serializer):
    id = serializers.CharField()
    type = serializers.ChoiceField(choices=ACTION_TYPE_CHOICES)
    priority = serializers.ChoiceField(choices=ACTION_PRIORITY_CHOICES)
    title = serializers.CharField()
    description = serializers.CharField()
    group = DashboardGroupSerializer(allow_null=True)
    source = DashboardActionSourceSerializer()
    amount_minor = serializers.IntegerField(allow_null=True)
    currency = serializers.CharField(allow_null=True)
    created_at = serializers.DateTimeField()
    due_at = serializers.DateTimeField(allow_null=True)
    allowed_actions = DashboardActionReferenceSerializer(many=True)


class DashboardActionItemListResponseSerializer(serializers.Serializer):
    results = DashboardActionItemSerializer(many=True)
    next_cursor = serializers.CharField(allow_null=True, required=False)


class DashboardActionItemQuerySerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=ACTION_TYPE_CHOICES, required=False)
    priority = serializers.ChoiceField(choices=ACTION_PRIORITY_CHOICES, required=False)
    group_id = serializers.UUIDField(required=False)
    cursor = serializers.CharField(required=False)
    page_size = serializers.IntegerField(required=False, min_value=1, max_value=100)


class DashboardActorSerializer(serializers.Serializer):
    user_id = serializers.UUIDField()
    art_name = serializers.CharField(allow_null=True, required=False)


class DashboardActivitySummarySerializer(serializers.Serializer):
    class Meta:
        ref_name = "DashboardActivitySummary"

    def to_representation(self, instance):
        return instance or {}


class DashboardActivityItemSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    type = serializers.ChoiceField(choices=ACTIVITY_TYPE_CHOICES)
    group = DashboardGroupSerializer()
    actor = DashboardActorSerializer(allow_null=True)
    occurred_at = serializers.DateTimeField()
    summary = serializers.JSONField()


class DashboardActivityListResponseSerializer(serializers.Serializer):
    results = DashboardActivityItemSerializer(many=True)
    next_cursor = serializers.CharField(allow_null=True, required=False)


class DashboardActivityQuerySerializer(serializers.Serializer):
    group_id = serializers.UUIDField(required=False)
    type = serializers.ChoiceField(choices=ACTIVITY_TYPE_CHOICES, required=False)
    from_ = serializers.DateField(required=False, source="from")
    to = serializers.DateField(required=False)
    cursor = serializers.CharField(required=False)
    page_size = serializers.IntegerField(required=False, min_value=1, max_value=100)
