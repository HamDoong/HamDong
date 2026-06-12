"""Serializers for identity service API."""

from rest_framework import serializers

from apps.identity.domain.models import User
from apps.identity.domain.rules import ArtNameRule


class PhoneNumberField(serializers.CharField):
    """Custom field for phone number validation."""

    def to_internal_value(self, data):
        if not isinstance(data, str):
            raise serializers.ValidationError("Phone number must be a string.")
        return data.strip()


class RequestOtpSerializer(serializers.Serializer):
    phone_number = PhoneNumberField(required=True)


class VerifyOtpSerializer(serializers.Serializer):
    phone_number = PhoneNumberField(required=True)
    code = serializers.CharField(required=True, min_length=6, max_length=6)

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


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True)
    new_password_confirm = serializers.CharField(required=True, write_only=True)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "phone_number",
            "display_name",
            "art_name",
            "first_name",
            "last_name",
            "avatar_url",
            "is_phone_verified",
            "role",
        ]
        read_only_fields = ["id", "phone_number", "is_phone_verified", "role"]


class UpdateUserSerializer(serializers.ModelSerializer):
    art_name = serializers.CharField(required=False, allow_blank=False)

    class Meta:
        model = User
        fields = ["display_name", "art_name", "first_name", "last_name"]

    def validate_art_name(self, value):
        normalized = ArtNameRule.normalize(value)
        if not ArtNameRule.is_valid(normalized):
            raise serializers.ValidationError("INVALID_ART_NAME")
        return normalized


class UserDetailSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    phone_number = serializers.CharField()
    display_name = serializers.CharField(allow_null=True)
    art_name = serializers.CharField(allow_null=True)
    first_name = serializers.CharField(allow_null=True)
    last_name = serializers.CharField(allow_null=True)
    is_phone_verified = serializers.BooleanField()
    role = serializers.CharField()
