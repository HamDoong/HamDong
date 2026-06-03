from django.conf import settings
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
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
    InviteCreateResponseSerializer,
    InvitePreviewSerializer,
    MemberSerializer,
    MessageSerializer,
    UpdateGroupSerializer,
)
from apps.groups.application.use_cases import (
    ArchiveGroupUseCase,
    CreateGroupUseCase,
    GetGroupDetailUseCase,
    InviteService,
    LeaveGroupUseCase,
    ListMembersUseCase,
    ListMyGroupsUseCase,
    RemoveMemberUseCase,
    UpdateGroupUseCase,
)
from apps.groups.domain import rules
from apps.groups.domain.models import GroupMember
from apps.groups.infrastructure.jwt_authentication import JWTAuthentication
from apps.groups.infrastructure.repositories import (
    GroupInviteRepository,
    GroupRepository,
)


def _error_response(code: str, message: str, http_status: int) -> Response:
    return Response(
        {"error": {"code": code, "message": message}},
        status=http_status,
    )


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

    @extend_schema(
        tags=["Groups"],
        summary="Create group",
        description="Create a new group and return the created group with the caller role.",
        request=CreateGroupSerializer,
        responses={201: GroupSerializer, 401: ErrorResponseSerializer},
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        group = CreateGroupUseCase().execute(
            title=serializer.validated_data["title"],
            description=serializer.validated_data.get("description", ""),
            group_type=serializer.validated_data.get("group_type", "GENERAL"),
            creator=request.user,
        )
        ctx = {"my_role_map": {str(group.id): "OWNER"}}
        return Response(
            GroupSerializer(group, context=ctx).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        tags=["Groups"],
        summary="List groups",
        description="List groups where the authenticated user is an active member.",
        responses={200: GroupSerializer(many=True), 401: ErrorResponseSerializer},
    )
    def get(self, request, *args, **kwargs):
        groups = ListMyGroupsUseCase().execute(request.user)
        member_qs = GroupMember.objects.filter(
            group__in=groups,
            user_id=request.user.sub,
            status="ACTIVE",
        )
        my_role_map = {str(member.group_id): member.role for member in member_qs}
        return Response(
            GroupSerializer(groups, many=True, context={"my_role_map": my_role_map}).data
        )


class GroupDetailView(GenericAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = UpdateGroupSerializer

    def get_object(self, group_id):
        return GroupRepository.get_by_id(group_id)

    @extend_schema(
        tags=["Groups"],
        summary="Get group detail",
        description="Return a single group visible to an active member.",
        responses={
            200: GroupSerializer,
            401: ErrorResponseSerializer,
            403: ErrorResponseSerializer,
            404: ErrorResponseSerializer,
        },
    )
    def get(self, request, group_id):
        group = self.get_object(group_id)
        if not group:
            return _error_response("GROUP_NOT_FOUND", "Group not found.", status.HTTP_404_NOT_FOUND)

        try:
            group = GetGroupDetailUseCase().execute(group, request.user)
        except PermissionError:
            return _error_response(
                "NOT_GROUP_MEMBER",
                "You are not an active member of this group.",
                status.HTTP_403_FORBIDDEN,
            )

        member = GroupMember.objects.filter(
            group=group,
            user_id=request.user.sub,
            status="ACTIVE",
        ).first()
        ctx = {"my_role_map": {str(group.id): member.role if member else None}}
        return Response(GroupSerializer(group, context=ctx).data)

    @extend_schema(
        tags=["Groups"],
        summary="Update group",
        description="Update mutable group fields when the caller is allowed to manage the group.",
        request=UpdateGroupSerializer,
        responses={
            200: GroupSerializer,
            401: ErrorResponseSerializer,
            403: ErrorResponseSerializer,
            404: ErrorResponseSerializer,
        },
    )
    def patch(self, request, group_id):
        group = self.get_object(group_id)
        if not group:
            return _error_response("GROUP_NOT_FOUND", "Group not found.", status.HTTP_404_NOT_FOUND)

        serializer = self.get_serializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        try:
            group = UpdateGroupUseCase().execute(group, request.user, **serializer.validated_data)
        except PermissionError:
            return _error_response(
                "PERMISSION_DENIED",
                "You do not have permission to update this group.",
                status.HTTP_403_FORBIDDEN,
            )

        member = GroupMember.objects.filter(
            group=group,
            user_id=request.user.sub,
            status="ACTIVE",
        ).first()
        ctx = {"my_role_map": {str(group.id): member.role if member else None}}
        return Response(GroupSerializer(group, context=ctx).data)


class GroupArchiveView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Groups"],
        summary="Archive group",
        description="Archive a group when the caller has permission.",
        responses={200: MessageSerializer, 401: ErrorResponseSerializer, 403: ErrorResponseSerializer, 404: ErrorResponseSerializer},
    )
    def post(self, request, group_id):
        group = GroupRepository.get_by_id(group_id)
        if not group:
            return _error_response("GROUP_NOT_FOUND", "Group not found.", status.HTTP_404_NOT_FOUND)

        try:
            ArchiveGroupUseCase().execute(group, request.user)
        except PermissionError:
            return _error_response(
                "PERMISSION_DENIED",
                "You do not have permission to archive this group.",
                status.HTTP_403_FORBIDDEN,
            )

        return Response({"message": "Group archived successfully."}, status=status.HTTP_200_OK)


class CreateInviteView(GenericAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = CreateInviteSerializer

    @extend_schema(
        tags=["Groups"],
        summary="Create group invite",
        description="Create an invite link for the target group.",
        request=CreateInviteSerializer,
        responses={201: InviteCreateResponseSerializer, 401: ErrorResponseSerializer, 403: ErrorResponseSerializer, 404: ErrorResponseSerializer},
    )
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
            return _error_response(
                "PERMISSION_DENIED",
                "You do not have permission to create invites for this group.",
                status.HTTP_403_FORBIDDEN,
            )
        except ValueError:
            return _error_response("INVALID_REQUEST", "Invalid invite request.", status.HTTP_400_BAD_REQUEST)

        base = getattr(settings, "INVITE_BASE_URL", None)
        if base:
            invite_url = f"{base.rstrip('/')}/api/v1/groups/invites/{raw_token}"
        else:
            invite_url = request.build_absolute_uri(f"/api/v1/groups/invites/{raw_token}")

        return Response(
            InviteCreateResponseSerializer(
                {"invite_id": str(invite.id), "invite_url": invite_url}
            ).data,
            status=status.HTTP_201_CREATED,
        )


class InvitePreviewView(APIView):
    authentication_classes = []
    permission_classes = []

    @extend_schema(
        tags=["Groups"],
        summary="Get invite detail",
        description="Return safe invite preview information by invite token.",
        responses={200: InvitePreviewSerializer, 404: ErrorResponseSerializer},
    )
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

    @extend_schema(
        tags=["Groups"],
        summary="Accept invite",
        description="Accept a group invite token as the authenticated user.",
        responses={200: MessageSerializer, 400: ErrorResponseSerializer, 401: ErrorResponseSerializer, 404: ErrorResponseSerializer},
    )
    def post(self, request, token):
        invite = InviteService().preview_invite(token)
        if not invite:
            return _error_response("INVITE_NOT_FOUND", "Invite not found.", status.HTTP_404_NOT_FOUND)

        try:
            result = InviteService().accept_invite(invite, request.user)
        except PermissionError as exc:
            return _error_response("INVALID_INVITE", str(exc), status.HTTP_400_BAD_REQUEST)

        if result == "ALREADY_GROUP_MEMBER":
            return Response({"message": "User is already a group member."}, status=status.HTTP_200_OK)

        return Response({"message": "Invite accepted successfully."}, status=status.HTTP_200_OK)


class RevokeInviteView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Groups"],
        summary="Revoke invite",
        description="Revoke a group invite by invite id.",
        responses={200: MessageSerializer, 401: ErrorResponseSerializer, 403: ErrorResponseSerializer, 404: ErrorResponseSerializer},
    )
    def post(self, request, group_id, invite_id):
        invite = GroupInviteRepository.get_by_id(invite_id)
        if not invite or str(invite.group.id) != str(group_id):
            return _error_response("INVITE_NOT_FOUND", "Invite not found.", status.HTTP_404_NOT_FOUND)

        try:
            InviteService().revoke_invite(invite, request.user)
        except PermissionError:
            return _error_response(
                "PERMISSION_DENIED",
                "You do not have permission to revoke this invite.",
                status.HTTP_403_FORBIDDEN,
            )

        return Response({"message": "Invite revoked successfully."}, status=status.HTTP_200_OK)


class MembersListView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Groups"],
        summary="List group members",
        description="List active group members with masked phone numbers.",
        responses={200: MemberSerializer(many=True), 401: ErrorResponseSerializer, 403: ErrorResponseSerializer, 404: ErrorResponseSerializer},
    )
    def get(self, request, group_id):
        group = GroupRepository.get_by_id(group_id)
        if not group:
            return _error_response("GROUP_NOT_FOUND", "Group not found.", status.HTTP_404_NOT_FOUND)

        if not rules.is_active_member(group, request.user.sub):
            return _error_response(
                "NOT_GROUP_MEMBER",
                "You are not an active member of this group.",
                status.HTTP_403_FORBIDDEN,
            )

        members = ListMembersUseCase().execute(group)
        return Response(
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
            ]
        )


class RemoveMemberView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Groups"],
        summary="Remove member",
        description="Remove a member from the group when the caller has the required role.",
        responses={200: MessageSerializer, 401: ErrorResponseSerializer, 403: ErrorResponseSerializer, 404: ErrorResponseSerializer},
    )
    def post(self, request, group_id, member_id):
        group = GroupRepository.get_by_id(group_id)
        if not group:
            return _error_response("GROUP_NOT_FOUND", "Group not found.", status.HTTP_404_NOT_FOUND)

        try:
            RemoveMemberUseCase().execute(group, request.user, member_id)
        except PermissionError:
            return _error_response(
                "PERMISSION_DENIED",
                "You do not have permission to remove this member.",
                status.HTTP_403_FORBIDDEN,
            )
        except ValueError:
            return _error_response("MEMBER_NOT_FOUND", "Member not found.", status.HTTP_404_NOT_FOUND)

        return Response({"message": "Member removed successfully."}, status=status.HTTP_200_OK)


class LeaveGroupView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Groups"],
        summary="Leave group",
        description="Leave a group as the authenticated member.",
        responses={200: MessageSerializer, 400: ErrorResponseSerializer, 401: ErrorResponseSerializer, 404: ErrorResponseSerializer},
    )
    def post(self, request, group_id):
        group = GroupRepository.get_by_id(group_id)
        if not group:
            return _error_response("GROUP_NOT_FOUND", "Group not found.", status.HTTP_404_NOT_FOUND)

        try:
            LeaveGroupUseCase().execute(group, request.user)
        except PermissionError:
            return _error_response(
                "PERMISSION_DENIED",
                "You do not have permission to leave this group.",
                status.HTTP_403_FORBIDDEN,
            )
        except ValueError:
            return _error_response("NOT_GROUP_MEMBER", "You are not an active member of this group.", status.HTTP_400_BAD_REQUEST)

        return Response({"message": "Left group successfully."}, status=status.HTTP_200_OK)


class HealthView(APIView):
    authentication_classes = []
    permission_classes = []

    @extend_schema(
        tags=["Groups"],
        summary="Health check",
        description="Return the service health payload for the group service.",
        responses={200: OpenApiResponse(description="Service health response")},
    )
    def get(self, request, *args, **kwargs):
        return Response(
            {
                "service": settings.SERVICE_NAME,
                "status": "ok",
                "version": settings.SERVICE_VERSION,
            }
        )
