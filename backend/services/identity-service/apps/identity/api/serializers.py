"""Serializers for identity service API."""

from rest_framework import serializers

from apps.identity.domain.models import User


class PhoneNumberField(serializers.CharField):
    """Custom field for phone number validation."""

    def to_internal_value(self, data):
        """Validate phone number type and return the raw value for domain validation."""
        if not isinstance(data, str):
            raise serializers.ValidationError("Phone number must be a string.")
        return data.strip()


class RequestOtpSerializer(serializers.Serializer):
    """Serializer for OTP request."""

    phone_number = PhoneNumberField(required=True)


class VerifyOtpSerializer(serializers.Serializer):
    """Serializer for OTP verification."""

    phone_number = PhoneNumberField(required=True)
    code = serializers.CharField(required=True, min_length=6, max_length=6)

    def validate_code(self, value):
        """Validate OTP code is numeric."""
        if not value.isdigit():
            raise serializers.ValidationError("OTP code must be numeric.")
        return value


class RefreshTokenSerializer(serializers.Serializer):
    """Serializer for token refresh."""

    refresh_token = serializers.CharField(required=True)


class LogoutSerializer(serializers.Serializer):
    """Serializer for logout."""

    refresh_token = serializers.CharField(required=True)


class UserSerializer(serializers.ModelSerializer):
    """Serializer for user data."""

    class Meta:
        model = User
        fields = [
            "id",
            "phone_number",
            "display_name",
            "first_name",
            "last_name",
            "avatar_url",
            "is_phone_verified",
            "role",
        ]
        read_only_fields = ["id", "phone_number", "is_phone_verified", "role"]


class UpdateUserSerializer(serializers.ModelSerializer):
    """Serializer for updating user profile."""

    class Meta:
        model = User
        fields = ["display_name", "first_name", "last_name"]


class UserDetailSerializer(serializers.Serializer):
    """Serializer for user detail in response."""

    id = serializers.UUIDField()
    phone_number = serializers.CharField()
    display_name = serializers.CharField(allow_null=True)
    first_name = serializers.CharField(allow_null=True)
    last_name = serializers.CharField(allow_null=True)
    is_phone_verified = serializers.BooleanField()
    role = serializers.CharField()
