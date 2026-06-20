"""Group service use cases (workflow logic)."""

from datetime import timedelta
from typing import List

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.groups.domain import rules
from apps.groups.domain.models import Group, GroupInvite, GroupMember
from apps.groups.infrastructure.rabbitmq_publisher import RabbitMQPublisher
from apps.groups.infrastructure.repositories import GroupInviteRepository, GroupMemberRepository, GroupRepository


def _build_title(title=None, title_parts=None):
    normalized_parts = rules.normalize_title_parts(title_parts) if title_parts is not None else None
    normalized_title = title.strip() if isinstance(title, str) else title
    if normalized_parts is not None:
        if title is None:
            normalized_title = " ".join(normalized_parts)
    if not normalized_title:
        raise ValueError("GROUP_TITLE_REQUIRED")
    return normalized_title, normalized_parts or []


class CreateGroupUseCase:
    def __init__(self, publisher: RabbitMQPublisher = None):
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

        GroupMemberRepository.add_owner(
            group=group,
            user_id=creator.sub,
            email=creator.email,
            art_name=getattr(creator, "art_name", None),
        )
        self.publisher.publish("GroupCreated", {"group_id": str(group.id), "created_by": creator.sub}, "group.created")
        self.publisher.publish(
            "GroupMemberJoined",
            {
                "group_id": str(group.id),
                "user_id": str(creator.sub),
                "email": creator.email,
                "art_name": getattr(creator, "art_name", None),
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
    def __init__(self, publisher: RabbitMQPublisher = None):
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
    def __init__(self, publisher: RabbitMQPublisher = None):
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
    def __init__(self, publisher: RabbitMQPublisher = None):
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
    def __init__(self, publisher: RabbitMQPublisher = None):
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
    def __init__(self, publisher: RabbitMQPublisher = None):
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
    def __init__(self, publisher: RabbitMQPublisher = None):
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
    def __init__(self, publisher: RabbitMQPublisher = None):
        self.publisher = publisher or RabbitMQPublisher()

    def _hash_token(self, token: str) -> str:
        import hashlib

        return hashlib.sha256(token.encode()).hexdigest()

    def create_invite(self, group: Group, creator, expires_in_hours: int = None, max_uses: int = None, invite_code: str = None):
        if not rules.is_owner_or_admin(group, creator.sub):
            raise PermissionError("not allowed")

        max_allowed = getattr(settings, "GROUP_INVITE_MAX_EXPIRES_HOURS", 168)
        if expires_in_hours is None:
            expires_in_hours = getattr(settings, "GROUP_INVITE_DEFAULT_EXPIRES_HOURS", 72)
        if expires_in_hours > max_allowed:
            raise ValueError("expires_in_hours too large")

        import secrets

        raw_token = secrets.token_urlsafe(32)
        token_hash = self._hash_token(raw_token)
        expires_at = timezone.now() + timedelta(hours=expires_in_hours) if expires_in_hours else None

        invite = GroupInviteRepository.create(
            group=group,
            created_by_user_id=creator.sub,
            token_hash=token_hash,
            invite_code=invite_code,
            max_uses=max_uses,
            expires_at=expires_at,
        )

        self.publisher.publish("GroupInviteCreated", {"group_id": str(group.id), "invite_id": str(invite.id), "created_by": creator.sub}, "group.invite.created")
        return invite, raw_token

    def preview_invite(self, raw_token: str):
        return GroupInviteRepository.get_by_token_hash(self._hash_token(raw_token))

    def accept_invite(self, invite: GroupInvite, user):
        if invite.status != "ACTIVE":
            raise PermissionError("INVALID_INVITE")
        if invite.group.status in ("ARCHIVED", "DELETED"):
            raise ValueError("GROUP_NOT_JOINABLE")
        if invite.expires_at and timezone.now() > invite.expires_at:
            raise PermissionError("INVITE_EXPIRED")
        if invite.max_uses and invite.used_count >= invite.max_uses:
            raise PermissionError("INVITE_MAX_USES_REACHED")

        member = GroupMember.objects.filter(group=invite.group, user_id=user.sub).first()
        join_reason = "NEW_JOIN"

        if member and member.status == "ACTIVE":
            raise ValueError("ALREADY_GROUP_MEMBER")

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
            member.art_name_snapshot = getattr(user, "art_name", None)
            member.save(
                update_fields=[
                    "status",
                    "role",
                    "left_at",
                    "removed_at",
                    "joined_at",
                    "email",
                    "art_name_snapshot",
                    "updated_at",
                ]
            )
        elif member and member.status == "LEFT":
            join_reason = "REJOIN_AFTER_LEFT"
            member.status = "ACTIVE"
            member.role = "MEMBER"
            member.left_at = None
            member.joined_at = timezone.now()
            member.email = user.email
            member.art_name_snapshot = getattr(user, "art_name", None)
            member.save(
                update_fields=[
                    "status",
                    "role",
                    "left_at",
                    "joined_at",
                    "email",
                    "art_name_snapshot",
                    "updated_at",
                ]
            )
        else:
            member = GroupMember.objects.create(
                group=invite.group,
                user_id=user.sub,
                email=user.email,
                art_name_snapshot=getattr(user, "art_name", None),
                role="MEMBER",
                status="ACTIVE",
            )

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
                "art_name": member.art_name_snapshot,
                "role": member.role,
                "status": member.status,
                "join_reason": join_reason,
            },
            "group.member.joined",
        )    
        return member

    def revoke_invite(self, invite, actor):
        if not rules.is_owner_or_admin(invite.group, actor.sub):
            raise PermissionError("not allowed")

        GroupInviteRepository.revoke(invite)
        self.publisher.publish("GroupInviteRevoked", {"group_id": str(invite.group.id), "invite_id": str(invite.id), "revoked_by": actor.sub}, "group.invite.revoked")
        return invite
