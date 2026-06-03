from rest_framework import serializers


class ReceiptUploadSerializer(serializers.Serializer):
    group_id = serializers.UUIDField()
    related_expense_id = serializers.UUIDField(required=False, allow_null=True)
    file = serializers.FileField()


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


class MessageSerializer(serializers.Serializer):
    message = serializers.CharField()
