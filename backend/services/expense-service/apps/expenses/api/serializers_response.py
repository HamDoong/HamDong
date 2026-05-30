from rest_framework import serializers


class ExpenseParticipantResponseSerializer(serializers.Serializer):
    user_id = serializers.UUIDField()
    phone_number = serializers.CharField(allow_blank=True, required=False)
    display_name_snapshot = serializers.CharField(allow_null=True, required=False)
    base_share_minor = serializers.IntegerField()
    tax_share_minor = serializers.IntegerField()
    service_fee_share_minor = serializers.IntegerField()
    total_share_minor = serializers.IntegerField()


class ExpenseResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    group_id = serializers.UUIDField()
    created_by_user_id = serializers.UUIDField()
    payer_user_id = serializers.UUIDField()
    title = serializers.CharField()
    description = serializers.CharField(allow_null=True)
    currency = serializers.CharField()
    base_amount_minor = serializers.IntegerField()
    tax_amount_minor = serializers.IntegerField()
    service_fee_amount_minor = serializers.IntegerField()
    total_amount_minor = serializers.IntegerField()
    split_method = serializers.CharField()
    status = serializers.CharField()
    expense_date = serializers.DateTimeField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    participants = ExpenseParticipantResponseSerializer(many=True)
