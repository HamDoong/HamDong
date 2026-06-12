from django.conf import settings
from django.utils import timezone
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.groups.api.serializers import (
    CreateGroupSerializer,
    CreateInviteSerializer,
    ErrorResponseSerializer,
    GroupSerializer,
    InviteAcceptResponseSerializer,
    InviteCreateResponseSerializer,
    InvitePreviewSerializer,
    MemberSerializer,
    MessageSerializer,
    RestoreGroupSerializer,
    UpdateGroupSerializer,
)
from apps.groups.application.use_cases import (
    ArchiveGroupUseCase,
    CreateGroupUseCase,
    DeleteGroupUseCase,
    GetGroupDetailUseCase,
    InviteService,
    LeaveGroupUseCase,
    ListMembersUseCase,
    ListMyGroupsUseCase,
    RemoveMemberUseCase,
    RestoreGroupUseCase,
    UpdateGroupUseCase,
)
from apps.groups.domain.models import GroupMember
from apps.groups.infrastructure.jwt_authentication import JWTAuthentication
from apps.groups.infrastructure.repositories import GroupInviteRepository, GroupRepository


def _error_response(code: str, message: str, http_status: int) -> Response:
    return Response({"error": {"code": code, "message": message}}, status=http_status)


def _mask_phone(phone_number: str | None) -> str | None:
    if not phone_number:
        return None
    phone_number = str(phone_number)
    if len(phone_number) < 4:
        return "****"
    return "****" + phone_number[-4:]


class GroupListCreateView(GenericAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = CreateGroupSerializer

    @extend_schema(tags=["Groups"], summary="Create group", request=CreateGroupSerializer, responses={201: GroupSerializer, 401: ErrorResponseSerializer})
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            if serializer.errors.get("title_parts") == ["INVALID_GROUP_TITLE_PARTS"]:
                return _error_response("INVALID_GROUP_TITLE_PARTS", "Group title parts are invalid.", status.HTTP_400_BAD_REQUEST)
            return Response({"error": {"code": "INVALID_REQUEST", "message": "Invalid request data.", "details": serializer.errors}}, status=status.HTTP_400_BAD_REQUEST)

        try:
            group = CreateGroupUseCase().execute(
                title=serializer.validated_data.get("title"),
                title_parts=serializer.validated_data.get("title_parts"),
                description=serializer.validated_data.get("description", ""),
                group_type=serializer.validated_data.get("group_type", "GENERAL"),
                creator=request.user,
            )
        except ValueError:
            return _error_response("INVALID_GROUP_TITLE_PARTS", "Group title parts are invalid.", status.HTTP_400_BAD_REQUEST)

        return Response(GroupSerializer(group, context={"my_role_map": {str(group.id): "OWNER"}}).data, status=status.HTTP_201_CREATED)

    @extend_schema(tags=["Groups"], summary="List groups", responses={200: GroupSerializer(many=True), 401: ErrorResponseSerializer})
    def get(self, request, *args, **kwargs):
        groups = ListMyGroupsUseCase().execute(request.user)
        member_qs = GroupMember.objects.filter(group__in=groups, user_id=request.user.sub, status="ACTIVE")
        my_role_map = {str(member.group_id): member.role for member in member_qs}
        return Response(GroupSerializer(groups, many=True, context={"my_role_map": my_role_map}).data)


class GroupDetailView(GenericAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = UpdateGroupSerializer

    def get_object(self, group_id):
        return GroupRepository.get_by_id(group_id)

    @extend_schema(tags=["Groups"], summary="Get group detail", responses={200: GroupSerializer, 401: ErrorResponseSerializer, 403: ErrorResponseSerializer, 404: ErrorResponseSerializer})
    def get(self, request, group_id):
        group = self.get_object(group_id)
        if not group or group.status == "DELETED":
            return _error_response("GROUP_NOT_FOUND", "Group not found.", status.HTTP_404_NOT_FOUND)

        try:
            group = GetGroupDetailUseCase().execute(group, request.user)
        except PermissionError:
            return _error_response("NOT_GROUP_MEMBER", "You are not an active member of this group.", status.HTTP_403_FORBIDDEN)

        member = GroupMember.objects.filter(group=group, user_id=request.user.sub, status="ACTIVE").first()
        return Response(GroupSerializer(group, context={"my_role_map": {str(group.id): member.role if member else None}}).data)

    @extend_schema(tags=["Groups"], summary="Update group", request=UpdateGroupSerializer, responses={200: GroupSerializer, 401: ErrorResponseSerializer, 403: ErrorResponseSerializer, 404: ErrorResponseSerializer})
    def patch(self, request, group_id):
        group = self.get_object(group_id)
        if not group or group.status == "DELETED":
            return _error_response("GROUP_NOT_FOUND", "Group not found.", status.HTTP_404_NOT_FOUND)

        serializer = self.get_serializer(data=request.data, partial=True)
        if not serializer.is_valid():
            if serializer.errors.get("title_parts") == ["INVALID_GROUP_TITLE_PARTS"]:
                return _error_response("INVALID_GROUP_TITLE_PARTS", "Group title parts are invalid.", status.HTTP_400_BAD_REQUEST)
            return Response({"error": {"code": "INVALID_REQUEST", "message": "Invalid request data.", "details": serializer.errors}}, status=status.HTTP_400_BAD_REQUEST)

        try:
            group = UpdateGroupUseCase().execute(group, request.user, **serializer.validated_data)
        except PermissionError:
            return _error_response("PERMISSION_DENIED", "You do not have permission to update this group.", status.HTTP_403_FORBIDDEN)
        except ValueError:
            return _error_response("INVALID_GROUP_TITLE_PARTS", "Group title parts are invalid.", status.HTTP_400_BAD_REQUEST)

        member = GroupMember.objects.filter(group=group, user_id=request.user.sub, status="ACTIVE").first()
        return Response(GroupSerializer(group, context={"my_role_map": {str(group.id): member.role if member else None}}).data)

    @extend_schema(tags=["Groups"], summary="Delete group", responses={200: MessageSerializer, 401: ErrorResponseSerializer, 403: ErrorResponseSerializer, 404: ErrorResponseSerializer})
    def delete(self, request, group_id):
        group = self.get_object(group_id)
        if not group:
            return _error_response("GROUP_NOT_FOUND", "Group not found.", status.HTTP_404_NOT_FOUND)
        try:
            DeleteGroupUseCase().execute(group, request.user)
        except PermissionError:
            return _error_response("GROUP_DELETE_FORBIDDEN", "Only group owner can delete this group.", status.HTTP_403_FORBIDDEN)
        return Response({"message": "Group deleted successfully."}, status=status.HTTP_200_OK)


class GroupArchiveView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Groups"], summary="Archive group", responses={200: MessageSerializer, 401: ErrorResponseSerializer, 403: ErrorResponseSerializer, 404: ErrorResponseSerializer})
    def post(self, request, group_id):
        group = GroupRepository.get_by_id(group_id)
        if not group:
            return _error_response("GROUP_NOT_FOUND", "Group not found.", status.HTTP_404_NOT_FOUND)

        try:
            ArchiveGroupUseCase().execute(group, request.user)
        except PermissionError:
            return _error_response("PERMISSION_DENIED", "You do not have permission to archive this group.", status.HTTP_403_FORBIDDEN)

        return Response({"message": "Group archived successfully."}, status=status.HTTP_200_OK)


class GroupRestoreView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Groups"], summary="Restore group", responses={200: RestoreGroupSerializer, 401: ErrorResponseSerializer, 403: ErrorResponseSerializer, 404: ErrorResponseSerializer})
    def post(self, request, group_id):
        group = GroupRepository.get_by_id(group_id)
        if not group:
            return _error_response("GROUP_NOT_FOUND", "Group not found.", status.HTTP_404_NOT_FOUND)
        try:
            group = RestoreGroupUseCase().execute(group, request.user)
        except PermissionError:
            return _error_response("GROUP_RESTORE_FORBIDDEN", "Only group owner or admin can restore this group.", status.HTTP_403_FORBIDDEN)
        except ValueError as exc:
            if str(exc) == "GROUP_NOT_ARCHIVED":
                return _error_response("GROUP_NOT_ARCHIVED", "Only archived groups can be restored.", status.HTTP_409_CONFLICT)
            return _error_response("GROUP_DELETED_CANNOT_RESTORE", "Deleted groups cannot be restored.", status.HTTP_409_CONFLICT)
        return Response(RestoreGroupSerializer(group).data, status=status.HTTP_200_OK)


class CreateInviteView(GenericAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = CreateInviteSerializer

    @extend_schema(tags=["Groups"], summary="Create group invite", request=CreateInviteSerializer, responses={201: InviteCreateResponseSerializer, 401: ErrorResponseSerializer, 403: ErrorResponseSerializer, 404: ErrorResponseSerializer})
    def post(self, request, group_id):
        group = GroupRepository.get_by_id(group_id)
        if not group:
            return _error_response("GROUP_NOT_FOUND", "Group not found.", status.HTTP_404_NOT_FOUND)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            invite, raw_token = InviteService().create_invite(
                group=group,
                creator=request.user,
                expires_in_hours=serializer.validated_data.get("expires_in_hours"),
                max_uses=serializer.validated_data.get("max_uses"),
                invite_code=serializer.validated_data.get("invite_code"),
            )
        except PermissionError:
            return _error_response("PERMISSION_DENIED", "You do not have permission to create invites for this group.", status.HTTP_403_FORBIDDEN)
        except ValueError:
            return _error_response("INVALID_REQUEST", "Invalid invite request.", status.HTTP_400_BAD_REQUEST)

        base = getattr(settings, "INVITE_BASE_URL", None)
        invite_url = f"{base.rstrip('/')}/api/v1/groups/invites/{raw_token}" if base else request.build_absolute_uri(f"/api/v1/groups/invites/{raw_token}")

        return Response(InviteCreateResponseSerializer({"invite_id": str(invite.id), "invite_url": invite_url}).data, status=status.HTTP_201_CREATED)


class InvitePreviewView(APIView):
    authentication_classes = []
    permission_classes = []

    @extend_schema(tags=["Groups"], summary="Get invite detail", responses={200: InvitePreviewSerializer, 404: ErrorResponseSerializer})
    def get(self, request, token):
        invite = InviteService().preview_invite(token)
        if not invite:
            return _error_response("INVITE_NOT_FOUND", "Invite not found.", status.HTTP_404_NOT_FOUND)

        if invite.expires_at and timezone.now() > invite.expires_at:
            return _error_response("INVITE_EXPIRED", "Invite expired.", status.HTTP_400_BAD_REQUEST)

        return Response(
            InvitePreviewSerializer(
                {
                    "group_id": invite.group.id,
                    "title": invite.group.title,
                    "group_type": invite.group.group_type,
                    "invite_status": invite.status,
                    "expires_at": invite.expires_at,
                }
            ).data
        )


class AcceptInviteView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Groups"], summary="Accept invite", responses={200: InviteAcceptResponseSerializer, 400: ErrorResponseSerializer, 401: ErrorResponseSerializer, 404: ErrorResponseSerializer})
    def post(self, request, token):
        invite = InviteService().preview_invite(token)
        if not invite:
            return _error_response("INVITE_NOT_FOUND", "Invite not found.", status.HTTP_404_NOT_FOUND)

        try:
            member = InviteService().accept_invite(invite, request.user)
        except PermissionError:
            return _error_response("INVALID_INVITE", "Invite is not valid.", status.HTTP_400_BAD_REQUEST)
        except ValueError as exc:
            if str(exc) == "ALREADY_GROUP_MEMBER":
                return _error_response("ALREADY_GROUP_MEMBER", "You are already an active member of this group.", status.HTTP_409_CONFLICT)
            if str(exc) == "NEW_INVITE_REQUIRED":
                return _error_response("NEW_INVITE_REQUIRED", "Removed members need a new invite to rejoin.", status.HTTP_409_CONFLICT)
            return _error_response("GROUP_NOT_JOINABLE", "This group cannot be joined.", status.HTTP_409_CONFLICT)

        return Response(
            InviteAcceptResponseSerializer(
                {
                    "group_id": invite.group.id,
                    "member_id": member.id,
                    "user_id": member.user_id,
                    "status": member.status,
                    "message": "You have joined the group successfully.",
                }
            ).data,
            status=status.HTTP_200_OK,
        )


class RevokeInviteView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Groups"], summary="Revoke invite", responses={200: MessageSerializer, 401: ErrorResponseSerializer, 403: ErrorResponseSerializer, 404: ErrorResponseSerializer})
    def post(self, request, group_id, invite_id):
        invite = GroupInviteRepository.get_by_id(invite_id)
        if not invite or str(invite.group_id) != str(group_id):
            return _error_response("INVITE_NOT_FOUND", "Invite not found.", status.HTTP_404_NOT_FOUND)

        try:
            InviteService().revoke_invite(invite, request.user)
        except PermissionError:
            return _error_response("PERMISSION_DENIED", "You do not have permission to revoke this invite.", status.HTTP_403_FORBIDDEN)

        return Response({"message": "Invite revoked successfully."}, status=status.HTTP_200_OK)


class MembersListView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Groups"], summary="List group members", responses={200: MemberSerializer(many=True), 401: ErrorResponseSerializer, 403: ErrorResponseSerializer, 404: ErrorResponseSerializer})
    def get(self, request, group_id):
        group = GroupRepository.get_by_id(group_id)
        if not group or group.status == "DELETED":
            return _error_response("GROUP_NOT_FOUND", "Group not found.", status.HTTP_404_NOT_FOUND)

        if not GroupMember.objects.filter(group=group, user_id=request.user.sub, status="ACTIVE").exists():
            return _error_response("NOT_GROUP_MEMBER", "You are not an active member of this group.", status.HTTP_403_FORBIDDEN)

        members = ListMembersUseCase().execute(group)
        return Response(
            MemberSerializer(
                [
                    {
                        "id": member.id,
                        "user_id": member.user_id,
                        "display_name_snapshot": member.display_name_snapshot,
                        "role": member.role,
                        "joined_at": member.joined_at,
                        "phone_number": _mask_phone(member.phone_number),
                    }
                    for member in members
                ],
                many=True,
            ).data
        )


class RemoveMemberView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Groups"], summary="Remove member", responses={200: MessageSerializer, 400: ErrorResponseSerializer, 401: ErrorResponseSerializer, 403: ErrorResponseSerializer, 404: ErrorResponseSerializer})
    def post(self, request, group_id, member_id):
        group = GroupRepository.get_by_id(group_id)
        if not group:
            return _error_response("GROUP_NOT_FOUND", "Group not found.", status.HTTP_404_NOT_FOUND)

        try:
            RemoveMemberUseCase().execute(group, request.user, member_id)
        except PermissionError:
            return _error_response("PERMISSION_DENIED", "You do not have permission to remove this member.", status.HTTP_403_FORBIDDEN)
        except ValueError:
            return _error_response("MEMBER_NOT_FOUND", "Member not found.", status.HTTP_404_NOT_FOUND)

        return Response({"message": "Member removed successfully."}, status=status.HTTP_200_OK)


class LeaveGroupView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Groups"], summary="Leave group", responses={200: MessageSerializer, 400: ErrorResponseSerializer, 401: ErrorResponseSerializer, 403: ErrorResponseSerializer, 404: ErrorResponseSerializer})
    def post(self, request, group_id):
        group = GroupRepository.get_by_id(group_id)
        if not group:
            return _error_response("GROUP_NOT_FOUND", "Group not found.", status.HTTP_404_NOT_FOUND)

        try:
            LeaveGroupUseCase().execute(group, request.user)
        except PermissionError:
            return _error_response("PERMISSION_DENIED", "You do not have permission to leave this group.", status.HTTP_403_FORBIDDEN)
        except ValueError:
            return _error_response("NOT_GROUP_MEMBER", "You are not an active member of this group.", status.HTTP_400_BAD_REQUEST)

        return Response({"message": "Left group successfully."}, status=status.HTTP_200_OK)


class HealthView(APIView):
    authentication_classes = []
    permission_classes = []

    @extend_schema(tags=["Groups"], summary="Health check", responses={200: OpenApiResponse(description="Service health response")})
    def get(self, request, *args, **kwargs):
        return Response(
            {
                "service": settings.SERVICE_NAME,
                "status": "ok",
                "version": settings.SERVICE_VERSION,
            }
        )
