
from __future__ import annotations

from rest_framework import serializers

from apps.notifications.domain.models import NotificationChannelChoices, NotificationMessageTypeChoices, NotificationStatusChoices


class AdminNotificationListQuerySerializer(serializers.Serializer):
    user_id = serializers.UUIDField(required=False)
    channel = serializers.ChoiceField(choices=NotificationChannelChoices.choices, required=False)
    status = serializers.ChoiceField(choices=NotificationStatusChoices.choices, required=False)
    type = serializers.ChoiceField(choices=NotificationMessageTypeChoices.choices, required=False)
    from_date = serializers.DateField(required=False, source="from")
    to = serializers.DateField(required=False)
    cursor = serializers.CharField(required=False)
    page_size = serializers.IntegerField(required=False, min_value=1, max_value=100, default=20)


class AdminNotificationItemSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    user_id = serializers.UUIDField(source="recipient_user_id", allow_null=True)
    channel = serializers.CharField()
    type = serializers.CharField(source="message_type")
    status = serializers.CharField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
