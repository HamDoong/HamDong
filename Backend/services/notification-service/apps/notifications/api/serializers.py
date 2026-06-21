from rest_framework import serializers

from apps.notifications.domain.models import NotificationMessage, NotificationMessageTypeChoices


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
    notification_type = serializers.CharField()
    title = serializers.CharField(required=False, allow_blank=True)
    body = serializers.CharField(required=False, allow_blank=False)
    metadata = serializers.JSONField(required=False)

    def validate(self, attrs):
        attrs["metadata"] = attrs.get("metadata", {})
        if attrs.get("notification_type") == NotificationMessageTypeChoices.CUSTOM and not attrs.get("body"):
            raise serializers.ValidationError({"body": "This field is required."})
        return attrs


class NotificationUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(required=False, allow_blank=True)
    body = serializers.CharField(required=False, allow_blank=False)
    metadata = serializers.JSONField(required=False)


class NotificationMessageSerializer(serializers.ModelSerializer):
    notification_type = serializers.CharField(source="message_type")
    body = serializers.CharField()
    metadata = serializers.JSONField()

    class Meta:
        model = NotificationMessage
        fields = [
            "id",
            "recipient_user_id",
            "channel",
            "notification_type",
            "title",
            "body",
            "metadata",
            "status",
            "created_at",
            "updated_at",
        ]


# Compatibility aliases.
TestSmsRequestSerializer = TestEmailRequestSerializer
TestSmsResponseSerializer = TestEmailResponseSerializer
