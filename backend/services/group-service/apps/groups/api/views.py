from django.conf import settings
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated

from apps.groups.api.serializers import (
    GroupSerializer,
    CreateGroupSerializer,
    UpdateGroupSerializer,
    GroupDetailSerializer,
    CreateInviteSerializer,
    InvitePreviewSerializer,
    InviteCreateResponseSerializer,
)
from apps.groups.infrastructure.jwt_authentication import JWTAuthentication
from apps.groups.infrastructure.repositories import GroupRepository, GroupMemberRepository, GroupInviteRepository
from apps.groups.domain.models import GroupMember, Group
# publisher is used inside use cases (rabbitmq_publisher)
from apps.groups.application.use_cases import (
    CreateGroupUseCase,
    ListMyGroupsUseCase,
    GetGroupDetailUseCase,
    UpdateGroupUseCase,
    ArchiveGroupUseCase,
    InviteService,
    ListMembersUseCase,
    RemoveMemberUseCase,
    LeaveGroupUseCase,
)
from apps.groups.domain import rules


class GroupListCreateView(GenericAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = []
    serializer_class = CreateGroupSerializer
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user = request.user

        use_case = CreateGroupUseCase()
        group = use_case.execute(title=data["title"], description=data.get("description", ""), group_type=data.get("group_type", "GENERAL"), creator=user)

        # respond with my_role injected
        ctx = {"my_role_map": {str(group.id): "OWNER"}}
        return Response(GroupSerializer(group, context=ctx).data, status=status.HTTP_201_CREATED)

    def get(self, request, *args, **kwargs):
        user = request.user
        use_case = ListMyGroupsUseCase()
        groups = use_case.execute(user)

        member_qs = GroupMember.objects.filter(group__in=groups, user_id=user.sub, status="ACTIVE")
        my_role_map = {str(m.group_id): m.role for m in member_qs}
        ctx = {"my_role_map": my_role_map}
        return Response(GroupSerializer(groups, many=True, context=ctx).data)


# Note: List is handled on GroupListCreateView.get


class GroupDetailView(GenericAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = []
    serializer_class = GroupDetailSerializer

    def get_object(self, group_id):
        return GroupRepository.get_by_id(group_id)

    def get(self, request, group_id):
        user = request.user
        group = self.get_object(group_id)
        if not group:
            return Response({"detail": "not found"}, status=status.HTTP_404_NOT_FOUND)

        use_case = GetGroupDetailUseCase()
        try:
            group = use_case.execute(group, user)
        except PermissionError:
            return Response({"detail": "forbidden"}, status=status.HTTP_403_FORBIDDEN)

        # determine role
        member = GroupMember.objects.filter(group=group, user_id=user.sub, status="ACTIVE").first()
        ctx = {"my_role_map": {str(group.id): member.role if member else None}}
        return Response(GroupSerializer(group, context=ctx).data)

    def patch(self, request, group_id):
        user = request.user
        group = self.get_object(group_id)
        if not group:
            return Response({"detail": "not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = UpdateGroupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        use_case = UpdateGroupUseCase()
        try:
            group = use_case.execute(group, user, **serializer.validated_data)
        except PermissionError:
            return Response({"detail": "forbidden"}, status=status.HTTP_403_FORBIDDEN)

        # return full group with my_role
        member = GroupMember.objects.filter(group=group, user_id=user.sub, status="ACTIVE").first()
        ctx = {"my_role_map": {str(group.id): member.role if member else None}}
        return Response(GroupSerializer(group, context=ctx).data)


class GroupArchiveView(APIView):
    authentication_classes = [JWTAuthentication]

    def post(self, request, group_id):
        user = request.user
        group = GroupRepository.get_by_id(group_id)
        if not group:
            return Response({"detail": "not found"}, status=status.HTTP_404_NOT_FOUND)

        use_case = ArchiveGroupUseCase()
        try:
            group = use_case.execute(group, user)
        except PermissionError:
            return Response({"detail": "forbidden"}, status=status.HTTP_403_FORBIDDEN)

        return Response({"detail": "archived"}, status=status.HTTP_200_OK)


class CreateInviteView(GenericAPIView):
    authentication_classes = [JWTAuthentication]
    serializer_class = CreateInviteSerializer

    def post(self, request, group_id):
        user = request.user
        group = GroupRepository.get_by_id(group_id)
        if not group:
            return Response({"detail": "not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        svc = InviteService()
        try:
            invite, raw_token = svc.create_invite(
                group=group,
                creator=user,
                expires_in_hours=serializer.validated_data.get("expires_in_hours"),
                max_uses=serializer.validated_data.get("max_uses"),
                invite_code=serializer.validated_data.get("invite_code"),
            )
        except PermissionError:
            return Response({"detail": "forbidden"}, status=status.HTTP_403_FORBIDDEN)
        except ValueError:
            return Response({"detail": "invalid"}, status=status.HTTP_400_BAD_REQUEST)

        # build invite_url
        base = getattr(settings, "INVITE_BASE_URL", None)
        if base:
            invite_url = f"{base.rstrip('/')}/api/v1/groups/invites/{raw_token}"
        else:
            invite_url = request.build_absolute_uri(f"/api/v1/groups/invites/{raw_token}")

        resp = {"invite_id": str(invite.id), "invite_url": invite_url}
        return Response(InviteCreateResponseSerializer(resp).data, status=status.HTTP_201_CREATED)


class InvitePreviewView(APIView):
    authentication_classes = []

    def get(self, request, token):
        svc = InviteService()
        invite = svc.preview_invite(token)
        if not invite:
            return Response({"detail": "not found"}, status=status.HTTP_404_NOT_FOUND)

        from django.utils import timezone

        if invite.expires_at and timezone.now() > invite.expires_at:
            return Response({"code": "INVITE_EXPIRED", "detail": "invite expired"}, status=status.HTTP_400_BAD_REQUEST)

        data = {
            "group_id": invite.group.id,
            "title": invite.group.title,
            "group_type": invite.group.group_type,
            "invite_status": invite.status,
            "expires_at": invite.expires_at,
        }
        return Response(data)


class AcceptInviteView(APIView):
    authentication_classes = [JWTAuthentication]

    def post(self, request, token):
        user = request.user
        svc = InviteService()
        invite = svc.preview_invite(token)
        if not invite:
            return Response({"detail": "not found"}, status=status.HTTP_404_NOT_FOUND)

        try:
            res = svc.accept_invite(invite, user)
        except PermissionError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        if res == "ALREADY_GROUP_MEMBER":
            return Response({"code": "ALREADY_GROUP_MEMBER", "detail": "user already in group"}, status=status.HTTP_200_OK)

        return Response({"detail": "joined"}, status=status.HTTP_200_OK)


class RevokeInviteView(APIView):
    authentication_classes = [JWTAuthentication]

    def post(self, request, group_id, invite_id):
        user = request.user
        invite = GroupInviteRepository.get_by_id(invite_id)
        if not invite or str(invite.group.id) != str(group_id):
            return Response({"detail": "not found"}, status=status.HTTP_404_NOT_FOUND)

        svc = InviteService()
        try:
            svc.revoke_invite(invite, user)
        except PermissionError:
            return Response({"detail": "forbidden"}, status=status.HTTP_403_FORBIDDEN)

        return Response({"detail": "revoked"}, status=status.HTTP_200_OK)


class MembersListView(APIView):
    authentication_classes = [JWTAuthentication]

    def get(self, request, group_id):
        user = request.user
        group = GroupRepository.get_by_id(group_id)
        if not group:
            return Response({"detail": "not found"}, status=status.HTTP_404_NOT_FOUND)

        # only active members can list
        if not rules.is_active_member(group, user.sub):
            return Response({"detail": "forbidden"}, status=status.HTTP_403_FORBIDDEN)

        use_case = ListMembersUseCase()
        members = use_case.execute(group)

        def mask_phone(p):
            if not p:
                return None
            p = str(p)
            return "****" + p[-4:]

        data = [
            {
                "id": m.id,
                "user_id": m.user_id,
                "display_name_snapshot": m.display_name_snapshot,
                "role": m.role,
                "joined_at": m.joined_at,
                "phone_number": mask_phone(m.phone_number),
            }
            for m in members
        ]
        return Response(data)


class RemoveMemberView(APIView):
    authentication_classes = [JWTAuthentication]

    def post(self, request, group_id, member_id):
        user = request.user
        group = GroupRepository.get_by_id(group_id)
        if not group:
            return Response({"detail": "not found"}, status=status.HTTP_404_NOT_FOUND)

        use_case = RemoveMemberUseCase()
        try:
            member = use_case.execute(group, user, member_id)
        except PermissionError:
            return Response({"detail": "forbidden"}, status=status.HTTP_403_FORBIDDEN)
        except ValueError:
            return Response({"detail": "not found"}, status=status.HTTP_404_NOT_FOUND)

        return Response({"detail": "removed"}, status=status.HTTP_200_OK)


class LeaveGroupView(APIView):
    authentication_classes = [JWTAuthentication]

    def post(self, request, group_id):
        user = request.user
        group = GroupRepository.get_by_id(group_id)
        if not group:
            return Response({"detail": "not found"}, status=status.HTTP_404_NOT_FOUND)

        use_case = LeaveGroupUseCase()
        try:
            member = use_case.execute(group, user)
        except PermissionError:
            return Response({"detail": "forbidden"}, status=status.HTTP_403_FORBIDDEN)
        except ValueError:
            return Response({"detail": "not a member"}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"detail": "left"}, status=status.HTTP_200_OK)


class HealthView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        return Response(
            {
                "service": settings.SERVICE_NAME,
                "status": "ok",
                "version": settings.SERVICE_VERSION,
            }
        )
