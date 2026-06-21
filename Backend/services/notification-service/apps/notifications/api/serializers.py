from __future__ import annotations

from rest_framework import serializers

from apps.notifications.domain.models import NotificationMessage, NotificationMessageTypeChoices, NotificationPriorityChoices


class TestEmailRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()
    message = serializers.CharField()


class TestEmailResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    provider = serializers.CharField()
    message_id = serializers.CharField(allow_null=True)


class NotificationCreateSerializer(serializers.Serializer):
    recipient_user_id = serializers.UUIDField(required=False)
    channel = serializers.CharField()
    notification_type = serializers.ChoiceField(choices=NotificationMessageTypeChoices.choices)
    title = serializers.CharField(required=False, allow_blank=True)
    body = serializers.CharField(required=False, allow_blank=False)
    metadata = serializers.JSONField(required=False)
    priority = serializers.ChoiceField(choices=NotificationPriorityChoices.choices, required=False)

    def validate(self, attrs):
        attrs["metadata"] = attrs.get("metadata", {})
        if attrs.get("notification_type") == NotificationMessageTypeChoices.CUSTOM and not attrs.get("body"):
            raise serializers.ValidationError({"body": "This field is required."})
        return attrs


class NotificationUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(required=False, allow_blank=True)
    body = serializers.CharField(required=False, allow_blank=False)
    metadata = serializers.JSONField(required=False)
    priority = serializers.ChoiceField(choices=NotificationPriorityChoices.choices, required=False)


class NotificationListQuerySerializer(serializers.Serializer):
    limit = serializers.IntegerField(required=False, min_value=1, max_value=100)
    cursor = serializers.CharField(required=False)
    page_size = serializers.IntegerField(required=False, min_value=1, max_value=100)
    is_read = serializers.BooleanField(required=False)
    priority = serializers.ChoiceField(choices=NotificationPriorityChoices.choices, required=False)
    notification_type = serializers.ChoiceField(choices=NotificationMessageTypeChoices.choices, required=False)

    def validate(self, attrs):
        if "limit" in attrs and ("cursor" in attrs or "page_size" in attrs):
            raise serializers.ValidationError(
                {"non_field_errors": ["Use either limit or cursor/page_size pagination, not both."]}
            )
        if "cursor" in attrs and "page_size" not in attrs:
            attrs["page_size"] = 20
        return attrs


class NotificationMessageSerializer(serializers.ModelSerializer):
    notification_type = serializers.CharField(source="message_type")
    body = serializers.CharField()
    message = serializers.CharField(source="body", read_only=True)
    metadata = serializers.JSONField()
    data = serializers.JSONField(source="metadata", read_only=True)

    class Meta:
        model = NotificationMessage
        fields = [
            "id",
            "recipient_user_id",
            "channel",
            "notification_type",
            "title",
            "body",
            "message",
            "metadata",
            "data",
            "status",
            "priority",
            "is_read",
            "read_at",
            "created_at",
            "updated_at",
        ]


class UnreadCountSerializer(serializers.Serializer):
    unread_count = serializers.IntegerField()
    important_unread_count = serializers.IntegerField()


class NotificationReadSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    is_read = serializers.BooleanField()
    read_at = serializers.DateTimeField(allow_null=True)


class NotificationsReadAllSerializer(serializers.Serializer):
    updated_count = serializers.IntegerField()
    read_at = serializers.DateTimeField()


# Compatibility aliases.
TestSmsRequestSerializer = TestEmailRequestSerializer
TestSmsResponseSerializer = TestEmailResponseSerializer
