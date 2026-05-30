from rest_framework import serializers

from apps.notifications.domain.models import NotificationMessage


class TestSmsRequestSerializer(serializers.Serializer):
    phone_number = serializers.CharField()
    message = serializers.CharField()


class TestSmsResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    provider = serializers.CharField()
    message_id = serializers.CharField(allow_null=True)


class NotificationMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationMessage
        fields = [
            "id",
            "channel",
            "message_type",
            "recipient_masked",
            "template_code",
            "status",
            "provider",
            "provider_message_id",
            "error_code",
            "error_message",
            "retry_count",
            "last_attempt_at",
            "sent_at",
            "created_at",
            "updated_at",
        ]
