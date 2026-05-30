from rest_framework import serializers


class CreateExpenseSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)
    payer_user_id = serializers.UUIDField()
    base_amount_minor = serializers.IntegerField()
    currency = serializers.CharField(default="IRR")
    split_method = serializers.ChoiceField(choices=[("EQUAL","EQUAL"),("CUSTOM_AMOUNT","CUSTOM_AMOUNT")])
    participant_user_ids = serializers.ListField(child=serializers.UUIDField(), required=False)
    participants = serializers.ListField(required=False)
    tax_type = serializers.ChoiceField(choices=[("NONE","NONE"),("PERCENTAGE","PERCENTAGE"),("FIXED","FIXED")], default="NONE")
    tax_percentage = serializers.DecimalField(max_digits=8, decimal_places=2, required=False)
    tax_amount_minor = serializers.IntegerField(required=False)
    service_fee_type = serializers.ChoiceField(choices=[("NONE","NONE"),("PERCENTAGE","PERCENTAGE"),("FIXED","FIXED")], default="NONE")
    service_fee_percentage = serializers.DecimalField(max_digits=8, decimal_places=2, required=False)
    service_fee_amount_minor = serializers.IntegerField(required=False)
    expense_date = serializers.DateTimeField(required=False)


class ParticipantSerializer(serializers.Serializer):
    user_id = serializers.UUIDField()
    base_share_minor = serializers.IntegerField()
from rest_framework import serializers


class PlaceholderSerializer(serializers.Serializer):
    message = serializers.CharField(required=False)
