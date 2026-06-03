from rest_framework import serializers


class ExpenseParticipantInputSerializer(serializers.Serializer):
    user_id = serializers.UUIDField()
    base_share_minor = serializers.IntegerField(min_value=0)


class ExpenseParticipantResponseSerializer(serializers.Serializer):
    user_id = serializers.UUIDField()
    phone_number = serializers.CharField()
    display_name_snapshot = serializers.CharField(allow_null=True, required=False)
    base_share_minor = serializers.IntegerField()
    tax_share_minor = serializers.IntegerField()
    service_fee_share_minor = serializers.IntegerField()
    total_share_minor = serializers.IntegerField()
    is_included = serializers.BooleanField(required=False)


class ExpenseResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    group_id = serializers.UUIDField()
    title = serializers.CharField()
    description = serializers.CharField(allow_null=True, required=False)
    payer_user_id = serializers.UUIDField()
    created_by_user_id = serializers.UUIDField()
    currency = serializers.CharField()
    base_amount_minor = serializers.IntegerField()
    tax_amount_minor = serializers.IntegerField()
    service_fee_amount_minor = serializers.IntegerField()
    total_amount_minor = serializers.IntegerField()
    split_method = serializers.CharField()
    status = serializers.CharField()
    expense_date = serializers.DateTimeField()
    participants = ExpenseParticipantResponseSerializer(many=True)
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class BaseExpenseWriteSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255, required=False)
    description = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    payer_user_id = serializers.UUIDField(required=False)
    base_amount_minor = serializers.IntegerField(required=False, min_value=1)
    currency = serializers.CharField(required=False, max_length=10, default="IRR")
    split_method = serializers.ChoiceField(
        choices=["EQUAL", "CUSTOM_AMOUNT"],
        required=False,
    )
    participant_user_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        allow_empty=False,
    )
    participants = ExpenseParticipantInputSerializer(many=True, required=False)

    tax_type = serializers.ChoiceField(
        choices=["NONE", "PERCENTAGE", "FIXED"],
        required=False,
        default="NONE",
    )
    tax_percentage = serializers.DecimalField(
        max_digits=7,
        decimal_places=4,
        required=False,
        allow_null=True,
    )
    tax_amount_minor = serializers.IntegerField(required=False, allow_null=True, min_value=0)

    service_fee_type = serializers.ChoiceField(
        choices=["NONE", "PERCENTAGE", "FIXED"],
        required=False,
        default="NONE",
    )
    service_fee_percentage = serializers.DecimalField(
        max_digits=7,
        decimal_places=4,
        required=False,
        allow_null=True,
    )
    service_fee_amount_minor = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=0,
    )

    expense_date = serializers.DateTimeField(required=False)

    def _validate_legacy_fields(self):
        legacy_fields = {"amount", "paid_by"}
        present_legacy_fields = sorted(legacy_fields.intersection(self.initial_data.keys()))
        if present_legacy_fields:
            raise serializers.ValidationError(
                {
                    field: "This legacy field is not supported. Use base_amount_minor or payer_user_id."
                    for field in present_legacy_fields
                }
            )

    def _validate_currency(self, data):
        currency = data.get("currency")
        if currency and currency != "IRR":
            raise serializers.ValidationError({"currency": "Only IRR is supported in this phase."})

    def _validate_split_fields(self, data, *, partial: bool):
        split_method = data.get("split_method")
        if partial and not split_method:
            return

        participant_user_ids = data.get("participant_user_ids")
        participants = data.get("participants")

        if split_method == "EQUAL":
            if not participant_user_ids:
                raise serializers.ValidationError(
                    {"participant_user_ids": "participant_user_ids is required for EQUAL split."}
                )
            if participants is not None:
                raise serializers.ValidationError(
                    {"participants": "participants is not allowed for EQUAL split."}
                )
        elif split_method == "CUSTOM_AMOUNT":
            if not participants:
                raise serializers.ValidationError(
                    {"participants": "participants is required for CUSTOM_AMOUNT split."}
                )
            if participant_user_ids is not None:
                raise serializers.ValidationError(
                    {"participant_user_ids": "participant_user_ids is not allowed for CUSTOM_AMOUNT split."}
                )

    def _validate_amount_config(self, data, *, prefix: str):
        amount_type = data.get(f"{prefix}_type")
        percentage = data.get(f"{prefix}_percentage")
        amount_minor = data.get(f"{prefix}_amount_minor")

        if amount_type == "PERCENTAGE" and percentage is None:
            raise serializers.ValidationError(
                {f"{prefix}_percentage": f"{prefix}_percentage is required for PERCENTAGE {prefix}."}
            )
        if amount_type == "FIXED" and amount_minor is None:
            raise serializers.ValidationError(
                {f"{prefix}_amount_minor": f"{prefix}_amount_minor is required for FIXED {prefix}."}
            )
        if amount_type == "NONE":
            data[f"{prefix}_percentage"] = None
            data[f"{prefix}_amount_minor"] = 0

    def validate(self, data):
        self._validate_legacy_fields()
        self._validate_currency(data)
        self._validate_split_fields(data, partial=self.partial)
        self._validate_amount_config(data, prefix="tax")
        self._validate_amount_config(data, prefix="service_fee")
        return data


class CreateExpenseSerializer(BaseExpenseWriteSerializer):
    title = serializers.CharField(max_length=255, required=True)
    payer_user_id = serializers.UUIDField(required=True)
    base_amount_minor = serializers.IntegerField(required=True, min_value=1)
    currency = serializers.CharField(required=False, max_length=10, default="IRR")
    split_method = serializers.ChoiceField(
        choices=["EQUAL", "CUSTOM_AMOUNT"],
        required=True,
    )


class UpdateExpenseSerializer(BaseExpenseWriteSerializer):
    pass
