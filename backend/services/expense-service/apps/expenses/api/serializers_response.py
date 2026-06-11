"""Response serializers and serializers helpers for expenses."""

from __future__ import annotations

from rest_framework import serializers


class ExpenseParticipantResponseSerializer(serializers.Serializer):
    user_id = serializers.UUIDField()
    phone_number = serializers.CharField()
    display_name_snapshot = serializers.CharField(allow_null=True)
    base_share_minor = serializers.IntegerField()
    tax_share_minor = serializers.IntegerField()
    service_fee_share_minor = serializers.IntegerField()
    total_share_minor = serializers.IntegerField()
    is_included = serializers.BooleanField()


class ExpenseResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    group_id = serializers.UUIDField()
    title = serializers.CharField()
    description = serializers.CharField(allow_null=True)
    payer_user_id = serializers.UUIDField()
    created_by_user_id = serializers.UUIDField()
    currency = serializers.CharField()
    base_amount_minor = serializers.IntegerField()
    tax_amount_minor = serializers.IntegerField()
    service_fee_amount_minor = serializers.IntegerField()
    total_amount_minor = serializers.IntegerField()
    split_method = serializers.CharField()
    status = serializers.CharField()
    participants = ExpenseParticipantResponseSerializer(many=True)
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    expense_date = serializers.DateTimeField(required=False)


def serialize_expense(expense) -> dict:
    """Convert an Expense model instance into the public API response contract."""
    return ExpenseResponseSerializer(
        {
            "id": expense.id,
            "group_id": expense.group_id,
            "title": expense.title,
            "description": expense.description,
            "payer_user_id": expense.payer_user_id,
            "created_by_user_id": expense.created_by_user_id,
            "currency": expense.currency,
            "base_amount_minor": expense.base_amount_minor,
            "tax_amount_minor": expense.tax_amount_minor,
            "service_fee_amount_minor": expense.service_fee_amount_minor,
            "total_amount_minor": expense.total_amount_minor,
            "split_method": expense.split_method,
            "status": expense.status,
            "participants": [
                {
                    "user_id": participant.user_id,
                    "phone_number": participant.phone_number,
                    "display_name_snapshot": participant.display_name_snapshot,
                    "base_share_minor": participant.base_share_minor,
                    "tax_share_minor": participant.tax_share_minor,
                    "service_fee_share_minor": participant.service_fee_share_minor,
                    "total_share_minor": participant.total_share_minor,
                    "is_included": participant.is_included,
                }
                for participant in expense.participants.all()
            ],
            "created_at": expense.created_at,
            "updated_at": expense.updated_at,
            "expense_date": expense.expense_date,
        }
    ).data
