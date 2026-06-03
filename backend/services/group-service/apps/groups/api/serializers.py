from rest_framework import serializers
from apps.groups.domain.models import Group


class GroupSerializer(serializers.ModelSerializer):
    my_role = serializers.SerializerMethodField()

    class Meta:
        model = Group
        fields = ["id", "title", "description", "group_type", "status", "created_by_user_id", "member_count", "created_at", "my_role"]

    def get_my_role(self, obj):
        # view should inject `context['my_role_map']` mapping
        mapping = self.context.get("my_role_map", {})
        return mapping.get(str(obj.id))


class CreateGroupSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)
    group_type = serializers.ChoiceField(choices=[("EVENT", "EVENT"), ("TRIP", "TRIP"), ("GENERAL", "GENERAL")], default="GENERAL")


class UpdateGroupSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    group_type = serializers.ChoiceField(choices=[("EVENT", "EVENT"), ("TRIP", "TRIP"), ("GENERAL", "GENERAL")], required=False)


class GroupDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ["id", "title", "description", "group_type", "status", "created_by_user_id", "member_count", "created_at"]


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
    phone_number = serializers.CharField()

class MessageSerializer(serializers.Serializer):
    message = serializers.CharField()
