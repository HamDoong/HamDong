from rest_framework import serializers

from apps.groups.domain.models import Group
from apps.groups.domain.rules import normalize_title_parts


class GroupSerializer(serializers.ModelSerializer):
    my_role = serializers.SerializerMethodField()
    display_title = serializers.ReadOnlyField()

    class Meta:
        model = Group
        fields = [
            "id",
            "title",
            "title_parts",
            "display_title",
            "description",
            "group_type",
            "status",
            "created_by_user_id",
            "member_count",
            "created_at",
            "restored_at",
            "my_role",
        ]

    def get_my_role(self, obj):
        mapping = self.context.get("my_role_map", {})
        return mapping.get(str(obj.id))


class CreateGroupSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255, required=False, allow_blank=False)
    title_parts = serializers.ListField(child=serializers.CharField(), required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    group_type = serializers.ChoiceField(
        choices=[("EVENT", "EVENT"), ("TRIP", "TRIP"), ("GENERAL", "GENERAL")],
        default="GENERAL",
    )

    def validate(self, attrs):
        if not attrs.get("title") and not attrs.get("title_parts"):
            raise serializers.ValidationError({"title": "This field is required."})
        if "title_parts" in attrs:
            try:
                attrs["title_parts"] = normalize_title_parts(attrs["title_parts"])
            except ValueError:
                raise serializers.ValidationError({"title_parts": "INVALID_GROUP_TITLE_PARTS"})
        return attrs


class UpdateGroupSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255, required=False)
    title_parts = serializers.ListField(child=serializers.CharField(), required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    group_type = serializers.ChoiceField(
        choices=[("EVENT", "EVENT"), ("TRIP", "TRIP"), ("GENERAL", "GENERAL")],
        required=False,
    )

    def validate(self, attrs):
        if "title_parts" in attrs:
            try:
                attrs["title_parts"] = normalize_title_parts(attrs["title_parts"])
            except ValueError:
                raise serializers.ValidationError({"title_parts": "INVALID_GROUP_TITLE_PARTS"})
        return attrs


class GroupDetailSerializer(serializers.ModelSerializer):
    display_title = serializers.ReadOnlyField()

    class Meta:
        model = Group
        fields = [
            "id",
            "title",
            "title_parts",
            "display_title",
            "description",
            "group_type",
            "status",
            "created_by_user_id",
            "member_count",
            "created_at",
            "restored_at",
        ]


class RestoreGroupSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    title = serializers.CharField()
    status = serializers.CharField()
    restored_at = serializers.DateTimeField()


class CreateInviteSerializer(serializers.Serializer):
    expires_in_hours = serializers.IntegerField(required=False)
    max_uses = serializers.IntegerField(required=False, allow_null=True)
    invite_code = serializers.CharField(required=False, allow_null=True, allow_blank=True)


class InvitePreviewSerializer(serializers.Serializer):
    group_id = serializers.UUIDField()
    title = serializers.CharField()
    group_type = serializers.CharField()
    invite_status = serializers.CharField()
    expires_at = serializers.DateTimeField(allow_null=True)


class InviteCreateResponseSerializer(serializers.Serializer):
    invite_id = serializers.UUIDField()
    invite_url = serializers.CharField()


class MemberSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    user_id = serializers.UUIDField()
    display_name_snapshot = serializers.CharField(allow_null=True)
    role = serializers.CharField()
    joined_at = serializers.DateTimeField()
    phone_number = serializers.CharField(allow_null=True)


class InviteAcceptResponseSerializer(serializers.Serializer):
    group_id = serializers.UUIDField()
    member_id = serializers.UUIDField()
    user_id = serializers.UUIDField()
    status = serializers.CharField()
    message = serializers.CharField()


class MessageSerializer(serializers.Serializer):
    message = serializers.CharField()


class ErrorDetailSerializer(serializers.Serializer):
    code = serializers.CharField()
    message = serializers.CharField()


class ErrorResponseSerializer(serializers.Serializer):
    error = ErrorDetailSerializer()
