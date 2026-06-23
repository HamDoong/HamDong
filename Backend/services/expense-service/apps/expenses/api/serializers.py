"""API serializers for the expense amount_minor contract."""

from __future__ import annotations

from rest_framework import serializers

from apps.expenses.domain.models import Expense


class CustomAmountParticipantSerializer(serializers.Serializer):
    user_id = serializers.UUIDField(required=True)
    base_share_minor = serializers.IntegerField(required=True, min_value=0)


class CreateExpenseSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255, required=True, allow_blank=False, trim_whitespace=True)
    description = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    payer_user_id = serializers.UUIDField(required=True)
    base_amount_minor = serializers.IntegerField(required=True, min_value=1)
    currency = serializers.ChoiceField(choices=["IRR"], default="IRR", required=False)
    split_method = serializers.ChoiceField(
        choices=[Expense.SPLIT_EQUAL, Expense.SPLIT_CUSTOM],
        required=True,
    )
    participant_user_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        allow_empty=False,
    )
    participants = CustomAmountParticipantSerializer(many=True, required=False)
    tax_type = serializers.ChoiceField(
        choices=[Expense.TAX_NONE, Expense.TAX_PERCENTAGE, Expense.TAX_FIXED],
        default=Expense.TAX_NONE,
        required=False,
    )
    tax_percentage = serializers.DecimalField(
        max_digits=7,
        decimal_places=4,
        required=False,
        allow_null=True,
    )
    tax_amount_minor = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    service_fee_type = serializers.ChoiceField(
        choices=[Expense.SERVICE_NONE, Expense.SERVICE_PERCENTAGE, Expense.SERVICE_FIXED],
        default=Expense.SERVICE_NONE,
        required=False,
    )
    service_fee_percentage = serializers.DecimalField(
        max_digits=7,
        decimal_places=4,
        required=False,
        allow_null=True,
    )
    service_fee_amount_minor = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    expense_date = serializers.DateTimeField(required=False)
    receipt_file_id = serializers.UUIDField(required=False, allow_null=True)
    receipt_url = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    payment_card_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        allow_empty=True,
    )

    def validate(self, data):
        self._reject_legacy_fields()

        split_method = data.get("split_method")
        if split_method == Expense.SPLIT_EQUAL and not data.get("participant_user_ids"):
            raise serializers.ValidationError(
                {"participant_user_ids": "EQUAL split requires participant_user_ids."}
            )

        if split_method == Expense.SPLIT_CUSTOM and not data.get("participants"):
            raise serializers.ValidationError(
                {"participants": "CUSTOM_AMOUNT split requires participants."}
            )

        if split_method == Expense.SPLIT_EQUAL and data.get("participants"):
            raise serializers.ValidationError(
                {"participants": "Use participant_user_ids for EQUAL split."}
            )

        if split_method == Expense.SPLIT_CUSTOM and data.get("participant_user_ids"):
            raise serializers.ValidationError(
                {"participant_user_ids": "Use participants for CUSTOM_AMOUNT split."}
            )

        self._validate_adjustment(
            data,
            type_field="tax_type",
            percentage_field="tax_percentage",
            amount_field="tax_amount_minor",
        )
        self._validate_adjustment(
            data,
            type_field="service_fee_type",
            percentage_field="service_fee_percentage",
            amount_field="service_fee_amount_minor",
        )
        return data

    def _reject_legacy_fields(self) -> None:
        legacy_fields = {"amount", "paid_by", "paidBy"}
        present = sorted(legacy_fields.intersection(set(self.initial_data)))
        if present:
            raise serializers.ValidationError(
                {
                    "legacy_fields": (
                        f"Unsupported legacy expense fields: {', '.join(present)}. "
                        "Use base_amount_minor and payer_user_id."
                    )
                }
            )

    def _validate_adjustment(
        self,
        data,
        type_field: str,
        percentage_field: str,
        amount_field: str,
    ) -> None:
        adjustment_type = data.get(type_field)
        if adjustment_type == "PERCENTAGE" and data.get(percentage_field) is None:
            raise serializers.ValidationError({percentage_field: "This field is required."})
        if adjustment_type == "FIXED" and data.get(amount_field) is None:
            raise serializers.ValidationError({amount_field: "This field is required."})


class UpdateExpenseSerializer(CreateExpenseSerializer):
    title = serializers.CharField(max_length=255, required=False, allow_blank=False, trim_whitespace=True)
    payer_user_id = serializers.UUIDField(required=False)
    base_amount_minor = serializers.IntegerField(required=False, min_value=1)
    split_method = serializers.ChoiceField(
        choices=[Expense.SPLIT_EQUAL, Expense.SPLIT_CUSTOM],
        required=False,
    )

    def validate(self, data):
        self._reject_legacy_fields()

        split_method = data.get("split_method")
        if split_method == Expense.SPLIT_EQUAL and data.get("participants"):
            raise serializers.ValidationError(
                {"participants": "Use participant_user_ids for EQUAL split."}
            )
        if split_method == Expense.SPLIT_CUSTOM and data.get("participant_user_ids"):
            raise serializers.ValidationError(
                {"participant_user_ids": "Use participants for CUSTOM_AMOUNT split."}
            )

        self._validate_adjustment(
            data,
            type_field="tax_type",
            percentage_field="tax_percentage",
            amount_field="tax_amount_minor",
        )
        self._validate_adjustment(
            data,
            type_field="service_fee_type",
            percentage_field="service_fee_percentage",
            amount_field="service_fee_amount_minor",
        )
        return data



class ExpensePaymentOptionsUpdateSerializer(serializers.Serializer):
    payment_card_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=True,
        allow_empty=True,
    )


class ExpensePaymentOptionsResponseSerializer(serializers.Serializer):
    expense_id = serializers.UUIDField()
    payee = serializers.DictField(required=False)
    payment_options = serializers.ListField(child=serializers.DictField())
