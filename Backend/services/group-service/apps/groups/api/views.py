from django.conf import settings
from django.utils import timezone
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.groups.api.serializers import (
    CreateDirectInviteSerializer,
    CreateGroupSerializer,
    CreateInviteSerializer,
    DirectInviteCreateResponseSerializer,
    DirectInviteDetailSerializer,
    DirectInviteListQuerySerializer,
    DirectInviteListResponseSerializer,
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
from apps.groups.application.member_display import build_member_payload
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
from apps.groups.domain.models import GroupInviteStatusChoices, GroupMember
from apps.groups.infrastructure.jwt_authentication import JWTAuthentication
from apps.groups.infrastructure.repositories import GroupInviteRepository, GroupRepository, UserProjectionRepository


def _error_response(code: str, message: str, http_status: int) -> Response:
    return Response({"error": {"code": code, "message": message}}, status=http_status)


def _mask_email(email: str | None) -> str | None:
    if not email:
        return None
    value = str(email).strip()
    if "@" not in value:
        return "***"
    local_part, domain = value.split("@", 1)
    if len(local_part) <= 2:
        masked_local = local_part[:1] + "***"
    else:
        masked_local = local_part[:2] + "***"
    return f"{masked_local}@{domain}"


def _direct_invite_payload(invite):
    invited_by_projection = UserProjectionRepository.get_by_identity_id(invite.created_by_user_id)
    return {
        "id": invite.id,
        "group": {
            "id": invite.group.id,
            "title": invite.group.display_title,
        },
        "invited_by": {
            "user_id": invite.created_by_user_id,
            "art_name": getattr(invited_by_projection, "art_name", "") or "",
        },
        "status": invite.status,
        "expires_at": invite.expires_at,
        "created_at": invite.created_at,
        "updated_at": invite.updated_at,
    }


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



class CreateDirectInviteView(GenericAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = CreateDirectInviteSerializer

    @extend_schema(
        tags=["Groups"],
        summary="Create direct group invitation",
        request=CreateDirectInviteSerializer,
        responses={201: DirectInviteCreateResponseSerializer, 400: ErrorResponseSerializer, 401: ErrorResponseSerializer, 403: ErrorResponseSerializer, 404: ErrorResponseSerializer},
    )
    def post(self, request, group_id):
        group = GroupRepository.get_by_id(group_id)
        if not group or group.status == "DELETED":
            return _error_response("GROUP_NOT_FOUND", "Group not found.", status.HTTP_404_NOT_FOUND)

        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response({"error": {"code": "INVALID_REQUEST", "message": "Invalid request data.", "details": serializer.errors}}, status=status.HTTP_400_BAD_REQUEST)

        try:
            invite = InviteService().create_direct_invite(
                group=group,
                creator=request.user,
                recipient_user_id=serializer.validated_data.get("recipient_user_id"),
                recipient_email=serializer.validated_data.get("recipient_email"),
                expires_in_hours=serializer.validated_data.get("expires_in_hours"),
            )
        except PermissionError as exc:
            if str(exc) == "NOT_GROUP_MEMBER":
                return _error_response("NOT_GROUP_MEMBER", "You are not an active member of this group.", status.HTTP_403_FORBIDDEN)
            return _error_response("PERMISSION_DENIED", "You do not have permission to create invites for this group.", status.HTTP_403_FORBIDDEN)
        except LookupError:
            return _error_response("GROUP_NOT_FOUND", "Group not found.", status.HTTP_404_NOT_FOUND)
        except ValueError as exc:
            error_map = {
                "GROUP_NOT_ACTIVE": ("GROUP_NOT_ACTIVE", "Group must be active.", status.HTTP_409_CONFLICT),
                "RECIPIENT_REQUIRED": ("RECIPIENT_REQUIRED", "Recipient is required.", status.HTTP_400_BAD_REQUEST),
                "INVALID_EXPIRES_IN_HOURS": ("INVALID_EXPIRES_IN_HOURS", "Expiration must be a positive number of hours.", status.HTTP_400_BAD_REQUEST),
                "EXPIRES_IN_HOURS_TOO_LARGE": ("EXPIRES_IN_HOURS_TOO_LARGE", "Expiration is too large.", status.HTTP_400_BAD_REQUEST),
                "RECIPIENT_NOT_FOUND": ("RECIPIENT_NOT_FOUND", "Recipient must be a registered user.", status.HTTP_400_BAD_REQUEST),
                "RECIPIENT_INACTIVE": ("RECIPIENT_INACTIVE", "Recipient must be active.", status.HTTP_400_BAD_REQUEST),
                "RECIPIENT_ALREADY_MEMBER": ("RECIPIENT_ALREADY_MEMBER", "Recipient is already a group member.", status.HTTP_409_CONFLICT),
                "DIRECT_INVITE_ALREADY_PENDING": ("DIRECT_INVITE_ALREADY_PENDING", "An active pending invitation already exists for this recipient.", status.HTTP_409_CONFLICT),
            }
            code, message, http_status = error_map.get(str(exc), ("INVALID_REQUEST", "Invalid invite request.", status.HTTP_400_BAD_REQUEST))
            return _error_response(code, message, http_status)

        return Response(
            DirectInviteCreateResponseSerializer(
                {
                    "id": invite.id,
                    "status": invite.status,
                    "expires_at": invite.expires_at,
                    "created_at": invite.created_at,
                }
            ).data,
            status=status.HTTP_201_CREATED,
        )


class MyDirectInvitationsView(GenericAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = DirectInviteListQuerySerializer

    @extend_schema(
        tags=["Groups"],
        summary="List my direct group invitations",
        responses={200: DirectInviteListResponseSerializer, 400: ErrorResponseSerializer, 401: ErrorResponseSerializer},
    )
    def get(self, request):
        serializer = self.get_serializer(data=request.query_params)
        if not serializer.is_valid():
            return Response({"error": {"code": "INVALID_REQUEST", "message": "Invalid request data.", "details": serializer.errors}}, status=status.HTTP_400_BAD_REQUEST)

        try:
            invites, next_cursor = InviteService().list_direct_invites(
                request.user.sub,
                status_filter=serializer.validated_data.get("status"),
                cursor=serializer.validated_data.get("cursor"),
                page_size=serializer.validated_data.get("page_size", 20),
            )
        except ValueError:
            return _error_response("INVALID_CURSOR", "Cursor is invalid.", status.HTTP_400_BAD_REQUEST)

        payload = {
            "results": [_direct_invite_payload(invite) for invite in invites],
            "next_cursor": next_cursor,
        }
        return Response(DirectInviteListResponseSerializer(payload).data)


class DirectInvitationDetailView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Groups"],
        summary="Get direct invitation detail",
        responses={200: DirectInviteDetailSerializer, 401: ErrorResponseSerializer, 404: ErrorResponseSerializer},
    )
    def get(self, request, invite_id):
        invite = InviteService().get_direct_invite_for_recipient(invite_id, request.user.sub)
        if not invite:
            return _error_response("INVITE_NOT_FOUND", "Invite not found.", status.HTTP_404_NOT_FOUND)
        return Response(DirectInviteDetailSerializer(_direct_invite_payload(invite)).data)


class AcceptDirectInvitationView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Groups"],
        summary="Accept direct invitation",
        request=None,
        responses={200: InviteAcceptResponseSerializer, 400: ErrorResponseSerializer, 401: ErrorResponseSerializer, 404: ErrorResponseSerializer, 409: ErrorResponseSerializer},
    )
    def post(self, request, invite_id):
        invite = GroupInviteRepository.get_by_id(invite_id)
        if not invite:
            return _error_response("INVITE_NOT_FOUND", "Invite not found.", status.HTTP_404_NOT_FOUND)
        try:
            member = InviteService().accept_direct_invite(invite, request.user)
        except PermissionError:
            return _error_response("INVITE_NOT_FOUND", "Invite not found.", status.HTTP_404_NOT_FOUND)
        except ValueError as exc:
            error_map = {
                "GROUP_NOT_JOINABLE": ("GROUP_NOT_JOINABLE", "This group cannot be joined.", status.HTTP_409_CONFLICT),
                "INVITE_EXPIRED": ("INVITE_EXPIRED", "Invite expired.", status.HTTP_409_CONFLICT),
                "INVITE_NOT_PENDING": ("INVITE_NOT_PENDING", "Invite is not pending.", status.HTTP_409_CONFLICT),
                "NEW_INVITE_REQUIRED": ("NEW_INVITE_REQUIRED", "Removed members need a new invite to rejoin.", status.HTTP_409_CONFLICT),
                "ALREADY_GROUP_MEMBER": ("ALREADY_GROUP_MEMBER", "You are already an active member of this group.", status.HTTP_409_CONFLICT),
                "INVITE_ALREADY_ACCEPTED": ("INVITE_ALREADY_ACCEPTED", "Invite was already accepted.", status.HTTP_409_CONFLICT),
            }
            code, message, http_status = error_map.get(str(exc), ("INVALID_INVITE", "Invite is not valid.", status.HTTP_400_BAD_REQUEST))
            return _error_response(code, message, http_status)

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


class RejectDirectInvitationView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Groups"],
        summary="Reject direct invitation",
        request=None,
        responses={200: MessageSerializer, 400: ErrorResponseSerializer, 401: ErrorResponseSerializer, 404: ErrorResponseSerializer, 409: ErrorResponseSerializer},
    )
    def post(self, request, invite_id):
        invite = GroupInviteRepository.get_by_id(invite_id)
        if not invite:
            return _error_response("INVITE_NOT_FOUND", "Invite not found.", status.HTTP_404_NOT_FOUND)
        try:
            InviteService().reject_direct_invite(invite, request.user)
        except PermissionError:
            return _error_response("INVITE_NOT_FOUND", "Invite not found.", status.HTTP_404_NOT_FOUND)
        except ValueError as exc:
            error_map = {
                "INVITE_EXPIRED": ("INVITE_EXPIRED", "Invite expired.", status.HTTP_409_CONFLICT),
                "INVITE_NOT_PENDING": ("INVITE_NOT_PENDING", "Invite is not pending.", status.HTTP_409_CONFLICT),
            }
            code, message, http_status = error_map.get(str(exc), ("INVALID_INVITE", "Invite is not valid.", status.HTTP_400_BAD_REQUEST))
            return _error_response(code, message, http_status)

        return Response({"message": "Invitation rejected successfully."}, status=status.HTTP_200_OK)



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

        members = list(ListMembersUseCase().execute(group))
        projection_map = UserProjectionRepository.get_map_by_identity_ids(member.user_id for member in members)
        payload = [
            build_member_payload(
                member,
                projection=projection_map.get(str(member.user_id)),
                masked_email=_mask_email(member.email),
            )
            for member in members
        ]
        return Response(MemberSerializer(payload, many=True).data)


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
