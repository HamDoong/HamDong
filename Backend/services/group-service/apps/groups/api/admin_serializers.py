
from __future__ import annotations

from rest_framework import serializers

from apps.groups.domain.models import GroupStatusChoices


class AdminGroupListQuerySerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=GroupStatusChoices.choices, required=False)
    owner_user_id = serializers.UUIDField(required=False)
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


class AdminGroupItemSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    title = serializers.CharField()
    status = serializers.CharField()
    owner_user_id = serializers.UUIDField(source="created_by_user_id")
    members_count = serializers.IntegerField(source="member_count")
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
