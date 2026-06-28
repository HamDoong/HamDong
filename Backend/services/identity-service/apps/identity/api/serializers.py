"""Serializers for identity service API."""

from __future__ import annotations

import re
from datetime import date

from django.conf import settings
from rest_framework import serializers

from apps.identity.domain.models import User
from apps.identity.domain.rules import (
    ArtNameRule,
    DateOfBirthRule,
    EmailRule,
    PhoneNumberRule,
    ProfileRule,
    VALID_OTP_PURPOSES,
)


class NormalizedEmailField(serializers.EmailField):
    def to_internal_value(self, data):
        value = super().to_internal_value(data)
        normalized = EmailRule.normalize(value)
        if not normalized:
            raise serializers.ValidationError("Invalid email address.")
        return normalized


class StrictDateField(serializers.DateField):
    default_error_messages = {
        "invalid": "Date has wrong format. Use YYYY-MM-DD.",
    }

    def to_internal_value(self, value):
        if value is None:
            return None
        if isinstance(value, bool):
            self.fail("invalid")
        if isinstance(value, str):
            if "T" in value.upper() or " " in value:
                self.fail("invalid")
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                self.fail("invalid")
        return super().to_internal_value(value)


class StrictOtpPurposeField(serializers.ChoiceField):
    default_error_messages = {
        "required": "Purpose is required.",
        "null": "Purpose is required.",
        "blank": "Purpose is required.",
        "invalid_choice": "Purpose must be LOGIN or SIGNUP.",
    }

    def __init__(self, **kwargs):
        kwargs.setdefault("choices", VALID_OTP_PURPOSES)
        kwargs.setdefault("required", True)
        kwargs.setdefault("allow_null", False)
        super().__init__(**kwargs)

    def to_internal_value(self, data):
        if data in ("", None):
            self.fail("required")
        return super().to_internal_value(data)


class TrimmedOptionalURLField(serializers.URLField):
    def to_internal_value(self, value):
        if value is None:
            return None
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return None
        return super().to_internal_value(value)


class StrictBooleanField(serializers.BooleanField):
    default_error_messages = {
        "invalid": "Must be a valid boolean.",
    }

    TRUE_VALUES = {True}
    FALSE_VALUES = {False}

    def to_internal_value(self, data):
        if data is True or data is False:
            return bool(data)
        self.fail("invalid")


class RequestOtpSerializer(serializers.Serializer):
    email = NormalizedEmailField(required=True)
    purpose = StrictOtpPurposeField()


class VerifyOtpSerializer(serializers.Serializer):
    email = NormalizedEmailField(required=True)
    code = serializers.CharField(required=True, min_length=6, max_length=6)
    purpose = StrictOtpPurposeField()

    def validate_code(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("OTP code must be numeric.")
        return value


class RefreshTokenSerializer(serializers.Serializer):
    refresh_token = serializers.CharField(required=True)


class LogoutSerializer(serializers.Serializer):
    refresh_token = serializers.CharField(required=True)


class PasswordSetSerializer(serializers.Serializer):
    new_password = serializers.CharField(required=True, write_only=True)
    new_password_confirm = serializers.CharField(required=True, write_only=True)


class PasswordLoginSerializer(serializers.Serializer):
    art_name = serializers.CharField(required=True)
    password = serializers.CharField(required=True, write_only=True)
    remember_me = StrictBooleanField(required=False, default=False)


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True)
    new_password_confirm = serializers.CharField(required=True, write_only=True)


class ForgotPasswordRequestSerializer(serializers.Serializer):
    email = NormalizedEmailField(required=True)


class ForgotPasswordVerifySerializer(serializers.Serializer):
    email = NormalizedEmailField(required=True)
    otp = serializers.CharField(required=True, min_length=6, max_length=6)

    def validate_otp(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("OTP code must be numeric.")
        return value


class PasswordResetSerializer(serializers.Serializer):
    reset_token = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True)
    new_password_confirm = serializers.CharField(required=True, write_only=True)


class SessionSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    remember_me = serializers.BooleanField()
    created_at = serializers.DateTimeField()
    last_used_at = serializers.DateTimeField()
    expires_at = serializers.DateTimeField()
    is_current = serializers.BooleanField()
    user_agent = serializers.CharField(allow_null=True)
    ip_address = serializers.CharField(allow_null=True)


class SessionListResponseSerializer(serializers.Serializer):
    results = SessionSerializer(many=True)


class UserSerializer(serializers.ModelSerializer):
    date_of_birth = serializers.DateField(allow_null=True, required=False)
    avatar_url = TrimmedOptionalURLField(allow_null=True, required=False)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "art_name",
            "first_name",
            "last_name",
            "display_name",
            "phone_number",
            "date_of_birth",
            "city",
            "bio",
            "avatar_url",
            "is_email_verified",
            "role",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "email", "is_email_verified", "role"]


class UpdateUserSerializer(serializers.Serializer):
    art_name = serializers.CharField(
        required=False, allow_blank=False, allow_null=False
    )
    first_name = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )
    last_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    display_name = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )
    phone_number = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )
    date_of_birth = StrictDateField(required=False, allow_null=True)
    city = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    bio = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    avatar_url = TrimmedOptionalURLField(
        required=False, allow_blank=True, allow_null=True
    )

    IGNORED_FIELDS = {
        "id",
        "email",
        "role",
        "is_active",
        "is_email_verified",
        "password",
        "password_hash",
    }

    def to_internal_value(self, data):
        if not isinstance(data, dict):
            raise serializers.ValidationError("Expected an object.")
        mutable = dict(data)
        for field_name in self.IGNORED_FIELDS:
            mutable.pop(field_name, None)
        return super().to_internal_value(mutable)

    def validate_art_name(self, value):
        normalized = ArtNameRule.normalize(value)
        if not ArtNameRule.is_valid(normalized):
            raise serializers.ValidationError("INVALID_ART_NAME")
        return normalized

    def validate_display_name(self, value):
        try:
            return ProfileRule.normalize_display_name(value)
        except ValueError:
            raise serializers.ValidationError("INVALID_DISPLAY_NAME")

    def validate_phone_number(self, value):
        try:
            return PhoneNumberRule.normalize(value)
        except ValueError:
            raise serializers.ValidationError("INVALID_PHONE_NUMBER")

    def validate_date_of_birth(self, value):
        try:
            return DateOfBirthRule.validate(value)
        except ValueError:
            raise serializers.ValidationError("INVALID_DATE_OF_BIRTH")

    def validate_city(self, value):
        try:
            return ProfileRule.normalize_city(value)
        except ValueError:
            raise serializers.ValidationError("INVALID_CITY")

    def validate_bio(self, value):
        try:
            return ProfileRule.normalize_bio(value)
        except ValueError:
            raise serializers.ValidationError("INVALID_BIO")

    def validate_first_name(self, value):
        try:
            return ProfileRule.normalize_optional_text(
                value, max_length=150, field_name="first_name"
            )
        except ValueError:
            raise serializers.ValidationError("INVALID_FIRST_NAME")

    def validate_last_name(self, value):
        try:
            return ProfileRule.normalize_optional_text(
                value, max_length=150, field_name="last_name"
            )
        except ValueError:
            raise serializers.ValidationError("INVALID_LAST_NAME")

    def validate(self, attrs):
        if "phone_number" in attrs and attrs.get("phone_number") == "":
            attrs["phone_number"] = None
        if "display_name" in attrs and attrs.get("display_name") == "":
            attrs["display_name"] = None
        if "city" in attrs and attrs.get("city") == "":
            attrs["city"] = None
        if "bio" in attrs and attrs.get("bio") == "":
            attrs["bio"] = None
        if "avatar_url" in attrs and attrs.get("avatar_url") == "":
            attrs["avatar_url"] = None
        return attrs


class UserDetailSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    email = serializers.EmailField()
    art_name = serializers.CharField()
    first_name = serializers.CharField(allow_null=True)
    last_name = serializers.CharField(allow_null=True)
    display_name = serializers.CharField(allow_null=True)
    phone_number = serializers.CharField(allow_null=True)
    date_of_birth = serializers.DateField(allow_null=True)
    city = serializers.CharField(allow_null=True)
    bio = serializers.CharField(allow_null=True)
    avatar_url = TrimmedOptionalURLField(allow_null=True, required=False)
    is_email_verified = serializers.BooleanField()
    role = serializers.CharField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class UserSearchQuerySerializer(serializers.Serializer):
    art_name = serializers.CharField(
        required=True, allow_blank=False, trim_whitespace=True
    )
    limit = serializers.IntegerField(
        required=False, min_value=1, max_value=20, default=10
    )
    exclude_me = serializers.BooleanField(required=False, default=True)

    def validate_art_name(self, value):
        if len(value) < 2:
            raise serializers.ValidationError("ART_NAME_QUERY_TOO_SHORT")
        if len(value) > 50:
            raise serializers.ValidationError("ART_NAME_QUERY_TOO_LONG")
        return value


class UserSearchResultSerializer(serializers.Serializer):
    user_id = serializers.UUIDField(source="id")
    art_name = serializers.CharField()
    avatar_url = TrimmedOptionalURLField(allow_null=True, required=False)


class UserSearchResponseSerializer(serializers.Serializer):
    items = UserSearchResultSerializer(many=True)
    count = serializers.IntegerField()
    query = serializers.CharField()


class PublicUserSerializer(serializers.Serializer):
    user_id = serializers.UUIDField(source="id")
    art_name = serializers.CharField()
    avatar_url = TrimmedOptionalURLField(allow_null=True, required=False)
    is_active = serializers.BooleanField()


class UserBankCardSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    masked_card_number = serializers.CharField(read_only=True)
    card_number_last4 = serializers.CharField(read_only=True)
    holder_name = serializers.CharField()
    bank_name = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    is_default = serializers.BooleanField(required=False, default=False)
    is_active = serializers.BooleanField(required=False, default=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)


class CreateUserBankCardSerializer(serializers.Serializer):
    card_number = serializers.CharField(required=True)
    holder_name = serializers.CharField(required=True)
    bank_name = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    is_default = serializers.BooleanField(required=False, default=False)


class UpdateUserBankCardSerializer(serializers.Serializer):
    holder_name = serializers.CharField(required=False)
    bank_name = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    is_default = serializers.BooleanField(required=False)
    is_active = serializers.BooleanField(required=False)
    card_number = serializers.CharField(required=False)

    def validate(self, attrs):
        immutable = {
            "card_number_hash",
            "encrypted_card_number",
            "card_number_last4",
            "user_id",
            "created_at",
            "id",
        }
        unexpected = immutable.intersection(self.initial_data.keys())
        if unexpected:
            raise serializers.ValidationError(
                {name: "This field may not be updated." for name in unexpected}
            )
        return attrs


class UserBankCardListResponseSerializer(serializers.Serializer):
    items = UserBankCardSerializer(many=True)


class BulkUserBankCardItemSerializer(serializers.Serializer):
    id = serializers.UUIDField(required=False)
    client_id = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    card_number = serializers.CharField(required=False)
    holder_name = serializers.CharField(required=False)
    bank_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    is_default = serializers.BooleanField(required=False)
    is_active = serializers.BooleanField(required=False)


class BulkUserBankCardSaveSerializer(serializers.Serializer):
    cards = BulkUserBankCardItemSerializer(many=True)
    deleted_card_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        allow_empty=True,
        default=list,
    )


class BulkUserBankCardSaveResponseSerializer(serializers.Serializer):
    items = serializers.ListField(child=serializers.DictField())
    deleted_card_ids = serializers.ListField(child=serializers.UUIDField())


class DeactivateAccountSerializer(serializers.Serializer):
    current_password = serializers.CharField(required=False, allow_blank=False)
    reason = serializers.CharField(
        required=False, allow_blank=True, allow_null=True, max_length=500
    )


class DeactivateAccountResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    message = serializers.CharField()
    deactivated_at = serializers.DateTimeField(required=False, allow_null=True)


class InternalPaymentContextBankCardsRequestSerializer(serializers.Serializer):
    owner_user_id = serializers.UUIDField(required=True)
    card_ids = serializers.ListField(
        child=serializers.UUIDField(), required=False, allow_empty=True
    )
