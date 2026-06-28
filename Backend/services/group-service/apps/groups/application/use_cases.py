"""Group service use cases (workflow logic)."""

from __future__ import annotations

from datetime import timedelta
from typing import List

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.groups.application.member_display import resolve_user_art_name
from apps.groups.domain import rules
from apps.groups.domain.models import (
    Group,
    GroupInvite,
    GroupInviteStatusChoices,
    GroupInviteTypeChoices,
    GroupMember,
)
from apps.groups.infrastructure.rabbitmq_publisher import RabbitMQPublisher
from apps.groups.infrastructure.repositories import (
    GroupInviteRepository,
    GroupMemberRepository,
    GroupRepository,
    UserProjectionRepository,
)


def _build_title(title=None, title_parts=None):
    normalized_parts = rules.normalize_title_parts(title_parts) if title_parts is not None else None
    normalized_title = title.strip() if isinstance(title, str) else title
    if normalized_parts is not None and title is None:
        normalized_title = " ".join(normalized_parts)
    if not normalized_title:
        raise ValueError("GROUP_TITLE_REQUIRED")
    return normalized_title, normalized_parts or []


class CreateGroupUseCase:
    def __init__(self, publisher: RabbitMQPublisher | None = None):
        self.publisher = publisher or RabbitMQPublisher()

    @transaction.atomic
    def execute(self, description: str, group_type: str, creator, title: str = None, title_parts=None) -> Group:
        final_title, normalized_parts = _build_title(title=title, title_parts=title_parts)
        group = GroupRepository.create(
            title=final_title,
            title_parts=normalized_parts,
            description=description,
            group_type=group_type,
            status="ACTIVE",
            created_by_user_id=creator.sub,
            created_by_email=creator.email,
            member_count=1,
        )
        creator_projection = UserProjectionRepository.get_by_identity_id(creator.sub)
        creator_art_name = resolve_user_art_name(creator, projection=creator_projection)

        GroupMemberRepository.add_owner(
            group=group,
            user_id=creator.sub,
            email=creator.email,
            art_name=creator_art_name,
        )
        self.publisher.publish("GroupCreated", {"group_id": str(group.id), "created_by": creator.sub}, "group.created")
        self.publisher.publish(
            "GroupMemberJoined",
            {
                "group_id": str(group.id),
                "user_id": str(creator.sub),
                "email": creator.email,
                "art_name": creator_art_name,
                "role": "OWNER",
                "status": "ACTIVE",
                "join_reason": "NEW_JOIN",
            },
            "group.member.joined",
        )
        return group


class ListMyGroupsUseCase:
    def execute(self, user) -> List[Group]:
        qs = GroupMember.objects.filter(user_id=user.sub, status="ACTIVE").select_related("group")
        return [member.group for member in qs if member.group.status != "DELETED"]


class GetGroupDetailUseCase:
    def execute(self, group: Group, user) -> Group:
        if group.status == "DELETED":
            raise LookupError("group deleted")
        if not rules.is_active_member(group, user.sub):
            raise PermissionError("not a member")
        return group


class UpdateGroupUseCase:
    def __init__(self, publisher: RabbitMQPublisher | None = None):
        self.publisher = publisher or RabbitMQPublisher()

    @transaction.atomic
    def execute(self, group: Group, user, **changes) -> Group:
        if not rules.is_owner_or_admin(group, user.sub):
            raise PermissionError("not allowed")

        if "title_parts" in changes:
            final_title, normalized_parts = _build_title(
                title=changes.get("title"),
                title_parts=changes.get("title_parts"),
            )
            group.title_parts = normalized_parts
            group.title = final_title

        if "title" in changes and changes["title"] is not None and "title_parts" not in changes:
            group.title = changes["title"].strip()

        if "description" in changes and changes["description"] is not None:
            group.description = changes["description"]
        if "group_type" in changes and changes["group_type"] is not None:
            group.group_type = changes["group_type"]

        group.version += 1
        group.save()

        self.publisher.publish("GroupUpdated", {"group_id": str(group.id), "updated_by": user.sub}, "group.updated")
        return group


class ArchiveGroupUseCase:
    def __init__(self, publisher: RabbitMQPublisher | None = None):
        self.publisher = publisher or RabbitMQPublisher()

    @transaction.atomic
    def execute(self, group: Group, user) -> Group:
        if not rules.is_owner(group, user.sub):
            raise PermissionError("not allowed")

        group.status = "ARCHIVED"
        group.version += 1
        group.save()

        self.publisher.publish("GroupArchived", {"group_id": str(group.id), "archived_by": user.sub}, "group.archived")
        return group


class RestoreGroupUseCase:
    def __init__(self, publisher: RabbitMQPublisher | None = None):
        self.publisher = publisher or RabbitMQPublisher()

    @transaction.atomic
    def execute(self, group: Group, user) -> Group:
        if not rules.is_owner_or_admin(group, user.sub):
            raise PermissionError("GROUP_RESTORE_FORBIDDEN")
        if group.status == "ACTIVE":
            raise ValueError("GROUP_NOT_ARCHIVED")
        if group.status == "DELETED":
            raise ValueError("GROUP_DELETED_CANNOT_RESTORE")

        group.status = "ACTIVE"
        group.restored_at = timezone.now()
        group.version += 1
        group.save(update_fields=["status", "restored_at", "version", "updated_at"])

        self.publisher.publish("GroupRestored", {"group_id": str(group.id), "restored_by": user.sub}, "group.restored")
        return group


class DeleteGroupUseCase:
    def __init__(self, publisher: RabbitMQPublisher | None = None):
        self.publisher = publisher or RabbitMQPublisher()

    @transaction.atomic
    def execute(self, group: Group, user) -> Group:
        if not rules.is_owner(group, user.sub):
            raise PermissionError("GROUP_DELETE_FORBIDDEN")
        if group.status == "DELETED":
            return group

        group.status = "DELETED"
        group.deleted_at = timezone.now()
        group.deleted_by_user_id = user.sub
        group.version += 1
        group.save(update_fields=["status", "deleted_at", "deleted_by_user_id", "version", "updated_at"])

        self.publisher.publish("GroupDeleted", {"group_id": str(group.id), "deleted_by": user.sub}, "group.deleted")
        return group


class ListMembersUseCase:
    def execute(self, group: Group):
        return GroupMember.objects.filter(group=group, status="ACTIVE")


class RemoveMemberUseCase:
    def __init__(self, publisher: RabbitMQPublisher | None = None):
        self.publisher = publisher or RabbitMQPublisher()

    @transaction.atomic
    def execute(self, group: Group, actor, member_id):
        if not rules.is_owner_or_admin(group, actor.sub):
            raise PermissionError("not allowed")

        member = GroupMember.objects.filter(group=group, id=member_id).first()
        if not member:
            raise ValueError("member not found")
        if member.role == "OWNER":
            raise PermissionError("cannot remove owner")

        member.status = "REMOVED"
        member.removed_at = timezone.now()
        member.save(update_fields=["status", "removed_at", "updated_at"])

        group.member_count = GroupMember.objects.filter(group=group, status="ACTIVE").count()
        group.save(update_fields=["member_count", "updated_at"])

        self.publisher.publish("GroupMemberRemoved", {"group_id": str(group.id), "member_id": str(member.id), "removed_by": actor.sub}, "group.member.removed")
        return member


class LeaveGroupUseCase:
    def __init__(self, publisher: RabbitMQPublisher | None = None):
        self.publisher = publisher or RabbitMQPublisher()

    @transaction.atomic
    def execute(self, group: Group, user):
        member = GroupMember.objects.filter(group=group, user_id=user.sub).first()
        if not member or member.status != "ACTIVE":
            raise ValueError("not a member")
        if member.role == "OWNER":
            raise PermissionError("owner cannot leave")

        member.status = "LEFT"
        member.left_at = timezone.now()
        member.save(update_fields=["status", "left_at", "updated_at"])

        group.member_count = GroupMember.objects.filter(group=group, status="ACTIVE").count()
        group.save(update_fields=["member_count", "updated_at"])

        self.publisher.publish("GroupMemberLeft", {"group_id": str(group.id), "member_id": str(member.id), "left_by": user.sub}, "group.member.left")
        return member


class InviteService:
    def __init__(self, publisher: RabbitMQPublisher | None = None):
        self.publisher = publisher or RabbitMQPublisher()

    def _hash_token(self, token: str) -> str:
        import hashlib

        return hashlib.sha256(token.encode()).hexdigest()

    def _resolve_invited_projection(self, *, recipient_user_id=None, recipient_email=None):
        projection = None
        if recipient_user_id:
            projection = UserProjectionRepository.get_by_identity_id(recipient_user_id)
        if not projection and recipient_email:
            projection = UserProjectionRepository.get_by_email(recipient_email)
        return projection

    def _validate_group_is_joinable(self, group: Group):
        if not group:
            raise LookupError("GROUP_NOT_FOUND")
        if group.status == "DELETED":
            raise LookupError("GROUP_NOT_FOUND")
        if group.status != "ACTIVE":
            raise ValueError("GROUP_NOT_ACTIVE")

    def _validate_inviter(self, group: Group, actor):
        if not GroupMemberRepository.is_active_member(group, actor.sub):
            raise PermissionError("NOT_GROUP_MEMBER")
        if not rules.is_owner_or_admin(group, actor.sub):
            raise PermissionError("INVITE_FORBIDDEN")

    def _recipient_art_name(self, projection):
        return getattr(projection, "art_name", None) or ""

    def create_invite(self, group: Group, creator, expires_in_hours: int = None, max_uses: int = None, invite_code: str = None):
        self._validate_group_is_joinable(group)
        self._validate_inviter(group, creator)

        max_allowed = getattr(settings, "GROUP_INVITE_MAX_EXPIRES_HOURS", 168)
        if expires_in_hours is None:
            expires_in_hours = getattr(settings, "GROUP_INVITE_DEFAULT_EXPIRES_HOURS", 72)
        if expires_in_hours > max_allowed:
            raise ValueError("EXPIRES_IN_HOURS_TOO_LARGE")

        import secrets

        raw_token = secrets.token_urlsafe(32)
        token_hash = self._hash_token(raw_token)
        expires_at = timezone.now() + timedelta(hours=expires_in_hours) if expires_in_hours else None

        invite = GroupInviteRepository.create(
            group=group,
            invite_type=GroupInviteTypeChoices.TOKEN,
            created_by_user_id=creator.sub,
            token_hash=token_hash,
            invite_code=invite_code,
            status=GroupInviteStatusChoices.ACTIVE,
            max_uses=max_uses,
            expires_at=expires_at,
        )

        self.publisher.publish("GroupInviteCreated", {"group_id": str(group.id), "invite_id": str(invite.id), "created_by": creator.sub}, "group.invite.created")
        return invite, raw_token

    def preview_invite(self, raw_token: str):
        return GroupInviteRepository.get_by_token_hash(self._hash_token(raw_token))

    @transaction.atomic
    def create_direct_invite(self, group: Group, creator, *, recipient_user_id=None, recipient_email=None, expires_in_hours: int | None = None):
        self._validate_group_is_joinable(group)
        self._validate_inviter(group, creator)

        if not recipient_user_id and not recipient_email:
            raise ValueError("RECIPIENT_REQUIRED")

        max_allowed = getattr(settings, "GROUP_INVITE_MAX_EXPIRES_HOURS", 168)
        if expires_in_hours is None:
            expires_in_hours = getattr(settings, "GROUP_INVITE_DEFAULT_EXPIRES_HOURS", 72)
        if expires_in_hours <= 0:
            raise ValueError("INVALID_EXPIRES_IN_HOURS")
        if expires_in_hours > max_allowed:
            raise ValueError("EXPIRES_IN_HOURS_TOO_LARGE")

        projection = self._resolve_invited_projection(
            recipient_user_id=recipient_user_id,
            recipient_email=recipient_email,
        )
        if not projection:
            raise ValueError("RECIPIENT_NOT_FOUND")
        if not projection.is_active:
            raise ValueError("RECIPIENT_INACTIVE")
        if GroupMemberRepository.is_active_member(group, projection.identity_user_id):
            raise ValueError("RECIPIENT_ALREADY_MEMBER")
        if GroupInviteRepository.has_pending_direct_invite(group.id, projection.identity_user_id):
            raise ValueError("DIRECT_INVITE_ALREADY_PENDING")

        expires_at = timezone.now() + timedelta(hours=expires_in_hours)
        invite = GroupInviteRepository.create(
            group=group,
            invite_type=GroupInviteTypeChoices.DIRECT,
            created_by_user_id=creator.sub,
            token_hash=None,
            status=GroupInviteStatusChoices.PENDING,
            recipient_user_id=projection.identity_user_id,
            recipient_email=projection.email,
            expires_at=expires_at,
        )

        self.publisher.publish(
            "GroupDirectInvitationCreated",
            {
                "invitation_id": str(invite.id),
                "group_id": str(group.id),
                "group_title": group.display_title,
                "recipient_user_id": str(projection.identity_user_id),
                "recipient_email": projection.email,
                "recipient_art_name": self._recipient_art_name(projection),
                "invited_by_user_id": str(creator.sub),
                "expires_at": expires_at.isoformat(),
            },
            "group.direct_invitation.created",
        )
        return invite

    def _accept_member_join(self, invite: GroupInvite, user):
        member = GroupMember.objects.filter(group=invite.group, user_id=user.sub).first()
        resolved_art_name = resolve_user_art_name(
            user,
            projection=UserProjectionRepository.get_by_identity_id(user.sub),
        )
        join_reason = "NEW_JOIN"

        if member and member.status == "ACTIVE":
            return member, resolved_art_name or member.art_name_snapshot, join_reason, False

        if member and member.status == "REMOVED":
            if member.removed_at and invite.created_at <= member.removed_at:
                raise ValueError("NEW_INVITE_REQUIRED")
            join_reason = "REJOIN_AFTER_REMOVED"
            member.status = "ACTIVE"
            member.role = "MEMBER"
            member.left_at = None
            member.removed_at = None
            member.joined_at = timezone.now()
            member.email = user.email
            update_fields = [
                "status",
                "role",
                "left_at",
                "removed_at",
                "joined_at",
                "email",
                "updated_at",
            ]
            if resolved_art_name:
                member.art_name_snapshot = resolved_art_name
                update_fields.append("art_name_snapshot")
            member.save(update_fields=update_fields)
            return member, resolved_art_name or member.art_name_snapshot, join_reason, True

        if member and member.status == "LEFT":
            join_reason = "REJOIN_AFTER_LEFT"
            member.status = "ACTIVE"
            member.role = "MEMBER"
            member.left_at = None
            member.joined_at = timezone.now()
            member.email = user.email
            update_fields = [
                "status",
                "role",
                "left_at",
                "joined_at",
                "email",
                "updated_at",
            ]
            if resolved_art_name:
                member.art_name_snapshot = resolved_art_name
                update_fields.append("art_name_snapshot")
            member.save(update_fields=update_fields)
            return member, resolved_art_name or member.art_name_snapshot, join_reason, True

        member = GroupMember.objects.create(
            group=invite.group,
            user_id=user.sub,
            email=user.email,
            art_name_snapshot=resolved_art_name,
            role="MEMBER",
            status="ACTIVE",
        )
        return member, resolved_art_name or member.art_name_snapshot, join_reason, True

    @transaction.atomic
    def accept_invite(self, invite: GroupInvite, user):
        if invite.invite_type != GroupInviteTypeChoices.TOKEN:
            raise PermissionError("INVALID_INVITE")
        if invite.status != GroupInviteStatusChoices.ACTIVE:
            raise PermissionError("INVALID_INVITE")
        if invite.group.status in ("ARCHIVED", "DELETED"):
            raise ValueError("GROUP_NOT_JOINABLE")
        if invite.expires_at and timezone.now() > invite.expires_at:
            raise PermissionError("INVITE_EXPIRED")
        if invite.max_uses and invite.used_count >= invite.max_uses:
            raise PermissionError("INVITE_MAX_USES_REACHED")

        member, art_name, join_reason, created_or_reactivated = self._accept_member_join(invite, user)
        if not created_or_reactivated:
            raise ValueError("ALREADY_GROUP_MEMBER")

        GroupInviteRepository.increment_used(invite)
        invite.group.member_count = GroupMember.objects.filter(group=invite.group, status="ACTIVE").count()
        invite.group.save(update_fields=["member_count", "updated_at"])

        self.publisher.publish("GroupInviteAccepted", {"group_id": str(invite.group.id), "invite_id": str(invite.id), "user_id": user.sub}, "group.invite.accepted")
        self.publisher.publish(
            "GroupMemberJoined",
            {
                "group_id": str(invite.group.id),
                "user_id": str(user.sub),
                "email": member.email,
                "art_name": art_name,
                "role": member.role,
                "status": member.status,
                "join_reason": join_reason,
            },
            "group.member.joined",
        )
        return member

    def accept_direct_invite(self, invite: GroupInvite, user):
        if invite.invite_type != GroupInviteTypeChoices.DIRECT:
            raise PermissionError("INVITE_NOT_FOUND")
        if str(invite.recipient_user_id) != str(user.sub):
            raise PermissionError("INVITE_NOT_FOUND")
        if invite.group.status != "ACTIVE":
            raise ValueError("GROUP_NOT_JOINABLE")
        if invite.expires_at and timezone.now() > invite.expires_at:
            GroupInviteRepository.mark_expired(invite)
            raise ValueError("INVITE_EXPIRED")
        if invite.status == GroupInviteStatusChoices.ACCEPTED:
            member = GroupMember.objects.filter(group=invite.group, user_id=user.sub, status="ACTIVE").first()
            if member:
                return member
            raise ValueError("INVITE_ALREADY_ACCEPTED")
        if invite.status != GroupInviteStatusChoices.PENDING:
            raise ValueError("INVITE_NOT_PENDING")

        with transaction.atomic():
            member, art_name, join_reason, created_or_reactivated = self._accept_member_join(invite, user)
            if not created_or_reactivated:
                raise ValueError("ALREADY_GROUP_MEMBER")

            GroupInviteRepository.mark_accepted(invite)
            invite.group.member_count = GroupMember.objects.filter(group=invite.group, status="ACTIVE").count()
            invite.group.save(update_fields=["member_count", "updated_at"])

        self.publisher.publish(
            "GroupDirectInvitationAccepted",
            {
                "invitation_id": str(invite.id),
                "group_id": str(invite.group.id),
                "group_title": invite.group.display_title,
                "recipient_user_id": str(user.sub),
                "recipient_email": user.email,
                "invited_by_user_id": str(invite.created_by_user_id),
                "accepted_at": invite.accepted_at.isoformat(),
            },
            "group.direct_invitation.accepted",
        )
        self.publisher.publish(
            "GroupMemberJoined",
            {
                "group_id": str(invite.group.id),
                "user_id": str(user.sub),
                "email": member.email,
                "art_name": art_name,
                "role": member.role,
                "status": member.status,
                "join_reason": join_reason,
            },
            "group.member.joined",
        )
        return member

    def reject_direct_invite(self, invite: GroupInvite, user):
        if invite.invite_type != GroupInviteTypeChoices.DIRECT:
            raise PermissionError("INVITE_NOT_FOUND")
        if str(invite.recipient_user_id) != str(user.sub):
            raise PermissionError("INVITE_NOT_FOUND")
        if invite.expires_at and timezone.now() > invite.expires_at:
            GroupInviteRepository.mark_expired(invite)
            raise ValueError("INVITE_EXPIRED")
        if invite.status != GroupInviteStatusChoices.PENDING:
            raise ValueError("INVITE_NOT_PENDING")

        with transaction.atomic():
            GroupInviteRepository.mark_rejected(invite)
        self.publisher.publish(
            "GroupDirectInvitationRejected",
            {
                "invitation_id": str(invite.id),
                "group_id": str(invite.group.id),
                "group_title": invite.group.display_title,
                "recipient_user_id": str(user.sub),
                "recipient_email": invite.recipient_email,
                "invited_by_user_id": str(invite.created_by_user_id),
                "rejected_at": invite.rejected_at.isoformat(),
            },
            "group.direct_invitation.rejected",
        )
        return invite

    def list_direct_invites(self, recipient_user_id, *, status_filter=None, cursor=None, page_size=20):
        return GroupInviteRepository.list_direct_for_recipient(
            recipient_user_id,
            status_filter=status_filter,
            cursor=cursor,
            page_size=page_size,
        )

    def get_direct_invite_for_recipient(self, invite_id, recipient_user_id):
        invite = GroupInviteRepository.get_direct_for_recipient(invite_id, recipient_user_id)
        if invite and invite.expires_at and timezone.now() > invite.expires_at and invite.status == GroupInviteStatusChoices.PENDING:
            GroupInviteRepository.mark_expired(invite)
        return invite

    @transaction.atomic
    def revoke_invite(self, invite, actor):
        self._validate_inviter(invite.group, actor)
        GroupInviteRepository.revoke(invite)
        if invite.invite_type == GroupInviteTypeChoices.DIRECT:
            self.publisher.publish(
                "GroupDirectInvitationRevoked",
                {
                    "invitation_id": str(invite.id),
                    "group_id": str(invite.group.id),
                    "group_title": invite.group.display_title,
                    "recipient_user_id": str(invite.recipient_user_id) if invite.recipient_user_id else None,
                    "recipient_email": invite.recipient_email,
                    "invited_by_user_id": str(invite.created_by_user_id),
                    "revoked_by_user_id": str(actor.sub),
                    "revoked_at": invite.revoked_at.isoformat(),
                },
                "group.direct_invitation.revoked",
            )
        else:
            self.publisher.publish("GroupInviteRevoked", {"group_id": str(invite.group.id), "invite_id": str(invite.id), "revoked_by": actor.sub}, "group.invite.revoked")
        return invite
