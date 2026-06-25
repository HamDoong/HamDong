
from __future__ import annotations

from rest_framework import serializers

from apps.settlements.domain.models import CurrencyChoices, InboxMessageStatusChoices, ManualSettlementStatusChoices, OutboxMessageStatusChoices, SettlementPlanItemStatusChoices


SETTLEMENT_STATUS_CHOICES = sorted(
    {
        choice[0]
        for choice in list(ManualSettlementStatusChoices.choices) + list(SettlementPlanItemStatusChoices.choices)
    }
)


class AdminSettlementListQuerySerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=[(item, item) for item in SETTLEMENT_STATUS_CHOICES], required=False)
    group_id = serializers.UUIDField(required=False)
    payer_user_id = serializers.UUIDField(required=False)
    payee_user_id = serializers.UUIDField(required=False)
    currency = serializers.ChoiceField(choices=CurrencyChoices.choices, required=False)
    from_date = serializers.DateField(required=False, source="from")
    to = serializers.DateField(required=False)
    cursor = serializers.CharField(required=False)
    page_size = serializers.IntegerField(required=False, min_value=1, max_value=100, default=20)

    def validate(self, attrs):
        start = attrs.get("from")
        end = attrs.get("to")
        if start and end and start > end:
            raise serializers.ValidationError({"to": "Must be greater than or equal to from."})
        return attrs


class AdminSettlementItemSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    source_type = serializers.CharField()
    group_id = serializers.UUIDField()
    payer_user_id = serializers.UUIDField()
    payee_user_id = serializers.UUIDField()
    amount_minor = serializers.IntegerField()
    currency = serializers.CharField()
    status = serializers.CharField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class AdminOutboxListQuerySerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=OutboxMessageStatusChoices.choices, required=False)
    event_type = serializers.CharField(required=False, allow_blank=False)
    from_date = serializers.DateField(required=False, source="from")
    to = serializers.DateField(required=False)
    cursor = serializers.CharField(required=False)
    page_size = serializers.IntegerField(required=False, min_value=1, max_value=100, default=20)


class AdminOutboxItemSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    event_id = serializers.UUIDField()
    event_type = serializers.CharField()
    status = serializers.CharField()
    payload = serializers.JSONField()
    retry_count = serializers.IntegerField()
    created_at = serializers.DateTimeField()
    published_at = serializers.DateTimeField(allow_null=True, required=False)


class AdminFailedEventListQuerySerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=InboxMessageStatusChoices.choices, required=False)
    event_type = serializers.CharField(required=False, allow_blank=False)
    from_date = serializers.DateField(required=False, source="from")
    to = serializers.DateField(required=False)
    cursor = serializers.CharField(required=False)
    page_size = serializers.IntegerField(required=False, min_value=1, max_value=100, default=20)


class AdminFailedEventItemSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    event_id = serializers.UUIDField()
    event_type = serializers.CharField()
    source_service = serializers.CharField()
    routing_key = serializers.CharField()
    status = serializers.CharField()
    error_message = serializers.CharField(allow_null=True, required=False)
    payload = serializers.JSONField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
