
from __future__ import annotations

from rest_framework import serializers

from apps.identity.domain.models import User


class CursorPaginatedResponseSerializer(serializers.Serializer):
    results = serializers.ListField()
    next_cursor = serializers.CharField(allow_null=True, required=False)


class AdminUserListQuerySerializer(serializers.Serializer):
    STATUS_CHOICES = [("ACTIVE", "ACTIVE"), ("INACTIVE", "INACTIVE")]

    status = serializers.ChoiceField(choices=STATUS_CHOICES, required=False)
    role = serializers.ChoiceField(choices=User.RoleChoices.choices, required=False)
    email = serializers.CharField(required=False, allow_blank=False)
    art_name = serializers.CharField(required=False, allow_blank=False)
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


class AdminUserItemSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    email = serializers.EmailField()
    art_name = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    role = serializers.CharField()
    is_active = serializers.BooleanField()
    is_email_verified = serializers.BooleanField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class AdminBankCardSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    holder_name = serializers.CharField()
    bank_name = serializers.CharField(allow_null=True, required=False)
    masked_card_number = serializers.CharField()
    card_number_last4 = serializers.CharField()
    is_default = serializers.BooleanField()
    is_active = serializers.BooleanField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class AdminUserDetailSerializer(AdminUserItemSerializer):
    first_name = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    last_name = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    phone_number = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    city = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    bio = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    avatar_url = serializers.URLField(allow_null=True, required=False)
    last_login_at = serializers.DateTimeField(allow_null=True, required=False)
    bank_cards = AdminBankCardSerializer(many=True)
