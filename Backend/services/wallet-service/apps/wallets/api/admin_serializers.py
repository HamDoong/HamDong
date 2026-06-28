
from __future__ import annotations

from rest_framework import serializers

from apps.wallets.domain.models import (
    CurrencyChoices,
    PaymentIntentStatusChoices,
    PaymentProviderChoices,
    PaymentPurposeChoices,
    WalletTransactionDirectionChoices,
    WalletTransactionStatusChoices,
    WalletTransactionTypeChoices,
)


class AdminWalletTransactionListQuerySerializer(serializers.Serializer):
    user_id = serializers.UUIDField(required=False)
    type = serializers.ChoiceField(choices=WalletTransactionTypeChoices.choices, required=False)
    status = serializers.ChoiceField(choices=WalletTransactionStatusChoices.choices, required=False)
    direction = serializers.ChoiceField(choices=WalletTransactionDirectionChoices.choices, required=False)
    currency = serializers.ChoiceField(choices=CurrencyChoices.choices, required=False)
    from_date = serializers.DateField(required=False, source="from")
    to = serializers.DateField(required=False)
    cursor = serializers.CharField(required=False)
    page_size = serializers.IntegerField(required=False, min_value=1, max_value=100, default=20)


class AdminWalletTransactionItemSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    wallet_id = serializers.UUIDField()
    user_id = serializers.UUIDField()
    type = serializers.CharField()
    status = serializers.CharField()
    direction = serializers.CharField()
    amount_minor = serializers.IntegerField()
    currency = serializers.CharField()
    reference_type = serializers.CharField(allow_null=True, required=False)
    reference_id = serializers.UUIDField(allow_null=True, required=False)
    created_at = serializers.DateTimeField()
    completed_at = serializers.DateTimeField(allow_null=True, required=False)


class AdminPaymentListQuerySerializer(serializers.Serializer):
    user_id = serializers.UUIDField(required=False)
    provider = serializers.ChoiceField(choices=PaymentProviderChoices.choices, required=False)
    status = serializers.ChoiceField(choices=PaymentIntentStatusChoices.choices, required=False)
    purpose = serializers.ChoiceField(choices=PaymentPurposeChoices.choices, required=False)
    currency = serializers.ChoiceField(choices=CurrencyChoices.choices, required=False)
    from_date = serializers.DateField(required=False, source="from")
    to = serializers.DateField(required=False)
    cursor = serializers.CharField(required=False)
    page_size = serializers.IntegerField(required=False, min_value=1, max_value=100, default=20)


class AdminPaymentItemSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    user_id = serializers.UUIDField()
    provider = serializers.CharField()
    purpose = serializers.CharField()
    status = serializers.CharField()
    amount_minor = serializers.IntegerField()
    currency = serializers.CharField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
