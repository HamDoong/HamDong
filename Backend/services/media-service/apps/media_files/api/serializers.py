from datetime import datetime, time, timezone as dt_timezone

from rest_framework import serializers
from django.utils import timezone


class ReceiptUploadSerializer(serializers.Serializer):
    group_id = serializers.UUIDField()
    related_expense_id = serializers.UUIDField(required=False, allow_null=True)
    file = serializers.FileField(use_url=False)


class MediaMetadataSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    group_id = serializers.UUIDField()
    related_expense_id = serializers.UUIDField(required=False, allow_null=True)
    file_type = serializers.CharField()
    original_filename = serializers.CharField()
    content_type = serializers.CharField()
    size_bytes = serializers.IntegerField()
    status = serializers.CharField()
    visibility = serializers.CharField()
    created_at = serializers.DateTimeField()


class MediaListItemSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    file_type = serializers.CharField()
    original_filename = serializers.CharField()
    content_type = serializers.CharField()
    size_bytes = serializers.IntegerField()
    created_at = serializers.DateTimeField()


class MediaListResponseSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    results = MediaListItemSerializer(many=True)


class GroupSummarySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    title = serializers.CharField()


class ReceiptListItemSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    expense_id = serializers.UUIDField(allow_null=True, required=False)
    group_id = serializers.UUIDField(required=False)
    group = GroupSummarySerializer(required=False)
    original_filename = serializers.CharField()
    content_type = serializers.CharField()
    size_bytes = serializers.IntegerField()
    uploaded_by_user_id = serializers.UUIDField()
    created_at = serializers.DateTimeField()
    download_url = serializers.CharField()


class ReceiptCursorListResponseSerializer(serializers.Serializer):
    results = ReceiptListItemSerializer(many=True)
    next_cursor = serializers.CharField(allow_null=True, required=False)


class ExpenseReceiptListQuerySerializer(serializers.Serializer):
    cursor = serializers.CharField(required=False)
    page_size = serializers.IntegerField(required=False, min_value=1, max_value=100, default=20)


class UserReceiptListQuerySerializer(serializers.Serializer):
    group_id = serializers.UUIDField(required=False)
    expense_id = serializers.UUIDField(required=False)
    uploaded_by_me = serializers.BooleanField(required=False)
    from_date = serializers.DateField(required=False)
    to_date = serializers.DateField(required=False)
    cursor = serializers.CharField(required=False)
    page_size = serializers.IntegerField(required=False, min_value=1, max_value=100, default=20)

    def validate(self, attrs):
        from_date = attrs.get("from_date")
        to_date = attrs.get("to_date")
        if from_date and to_date and from_date > to_date:
            raise serializers.ValidationError({"to": ["Must be on or after from."]})
        return attrs

    def to_internal_value(self, data):
        mutable = dict(data)
        if "from" in mutable and "from_date" not in mutable:
            mutable["from_date"] = mutable["from"]
        return super().to_internal_value(mutable)

    @staticmethod
    def start_of_day(value):
        return timezone.make_aware(datetime.combine(value, time.min), dt_timezone.utc)

    @staticmethod
    def end_of_day(value):
        return timezone.make_aware(datetime.combine(value, time.max), dt_timezone.utc)


class MessageSerializer(serializers.Serializer):
    message = serializers.CharField()
