"""Group service use cases (workflow logic)."""

from typing import List
from django.db import transaction
from apps.groups.infrastructure.repositories import (
    GroupRepository,
    GroupMemberRepository,
    UserProjectionRepository,
)
from apps.groups.infrastructure.repositories import GroupInviteRepository
from apps.groups.infrastructure.rabbitmq_publisher import RabbitMQPublisher
from apps.groups.domain.models import Group, GroupMember, GroupInvite
from apps.groups.domain import rules


class CreateGroupUseCase:
    def __init__(self, publisher: RabbitMQPublisher = None):
        self.publisher = publisher or RabbitMQPublisher()

    @transaction.atomic
    def execute(self, title: str, description: str, group_type: str, creator) -> Group:
        group = GroupRepository.create(
            title=title,
            description=description,
            group_type=group_type,
            status="ACTIVE",
            created_by_user_id=creator.sub,
            created_by_phone_number=creator.phone_number,
            member_count=1,
        )

        GroupMemberRepository.add_owner(group=group, user_id=creator.sub, phone_number=creator.phone_number, display_name=getattr(creator, "display_name", None))

        # publish events
        self.publisher.publish("GroupCreated", {"group_id": str(group.id), "created_by": creator.sub}, "group.created")
        self.publisher.publish("GroupMemberJoined", {"group_id": str(group.id), "user_id": creator.sub, "role": "OWNER"}, "group.member.joined")

        return group


class ListMyGroupsUseCase:
    def execute(self, user) -> List[Group]:
        qs = GroupMember.objects.filter(user_id=user.sub, status="ACTIVE").select_related("group")
        return [m.group for m in qs]


class GetGroupDetailUseCase:
    def execute(self, group: Group, user) -> Group:
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

        for k, v in changes.items():
            setattr(group, k, v)
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


class ListMembersUseCase:
    def execute(self, group: Group):
        return GroupMember.objects.filter(group=group, status="ACTIVE")


class RemoveMemberUseCase:
    def __init__(self, publisher: RabbitMQPublisher = None):
        self.publisher = publisher or RabbitMQPublisher()

    def execute(self, group: Group, actor, member_id: str):
        # permission
        if not rules.is_owner_or_admin(group, actor.sub):
            raise PermissionError("not allowed")

        member = GroupMember.objects.filter(group=group, id=member_id).first()
        if not member:
            raise ValueError("member not found")

        # cannot remove self
        if str(member.user_id) == str(actor.sub):
            raise PermissionError("cannot remove self")

        # admin cannot remove owner
        if member.role == "OWNER":
            # only owner can remove owner (not allowed here)
            raise PermissionError("cannot remove owner")

        # perform removal
        from django.utils import timezone

        member.status = "REMOVED"
        member.removed_at = timezone.now()
        member.save(update_fields=["status", "removed_at"])

        group.member_count = GroupMember.objects.filter(group=group, status="ACTIVE").count()
        group.save(update_fields=["member_count"])

        self.publisher.publish("GroupMemberRemoved", {"group_id": str(group.id), "member_id": str(member.id), "removed_by": actor.sub}, "group.member.removed")
        return member


class LeaveGroupUseCase:
    def __init__(self, publisher: RabbitMQPublisher = None):
        self.publisher = publisher or RabbitMQPublisher()

    def execute(self, group: Group, user):
        member = GroupMember.objects.filter(group=group, user_id=user.sub).first()
        if not member or member.status != "ACTIVE":
            raise ValueError("not a member")

        # owner cannot leave
        if member.role == "OWNER":
            raise PermissionError("owner cannot leave")

        from django.utils import timezone

        member.status = "LEFT"
        member.left_at = timezone.now()
        member.save(update_fields=["status", "left_at"])

        group.member_count = GroupMember.objects.filter(group=group, status="ACTIVE").count()
        group.save(update_fields=["member_count"])

        self.publisher.publish("GroupMemberLeft", {"group_id": str(group.id), "member_id": str(member.id), "left_by": user.sub}, "group.member.left")
        return member


class InviteService:
    def __init__(self, publisher: RabbitMQPublisher = None):
        self.publisher = publisher or RabbitMQPublisher()

    def _hash_token(self, token: str) -> str:
        import hashlib

        return hashlib.sha256(token.encode()).hexdigest()

    def create_invite(self, group: Group, creator, expires_in_hours: int = None, max_uses: int = None, invite_code: str = None):
        # permission
        if not rules.is_owner_or_admin(group, creator.sub):
            raise PermissionError("not allowed")

        # enforce env max
        from django.conf import settings

        max_allowed = getattr(settings, "GROUP_INVITE_MAX_EXPIRES_HOURS", 168)
        if expires_in_hours is None:
            expires_in_hours = getattr(settings, "GROUP_INVITE_DEFAULT_EXPIRES_HOURS", 72)
        if expires_in_hours > max_allowed:
            raise ValueError("expires_in_hours too large")

        import secrets
        from django.utils import timezone
        from datetime import timedelta

        raw_token = secrets.token_urlsafe(32)
        token_hash = self._hash_token(raw_token)

        expires_at = None
        if expires_in_hours:
            expires_at = timezone.now() + timedelta(hours=expires_in_hours)

        invite = GroupInviteRepository.create(
            group=group,
            created_by_user_id=creator.sub,
            token_hash=token_hash,
            invite_code=invite_code,
            status="ACTIVE",
            max_uses=max_uses,
            expires_at=expires_at,
        )

        # publish without raw token
        # publish event without raw token
        self.publisher.publish("GroupInviteCreated", {"group_id": str(group.id), "invite_id": str(invite.id), "created_by": creator.sub}, "group.invite.created")

        return invite, raw_token


    def preview_invite(self, raw_token: str):
        token_hash = self._hash_token(raw_token)
        invite = GroupInviteRepository.get_by_token_hash(token_hash)
        if not invite:
            return None

        # include status and expires
        return invite


    def accept_invite(self, invite, user):
        from django.utils import timezone

        # checks
        if invite.status != "ACTIVE":
            raise PermissionError("invite not active")

        if invite.expires_at and timezone.now() > invite.expires_at:
            raise PermissionError("invite expired")

        if invite.max_uses and invite.used_count >= invite.max_uses:
            raise PermissionError("invite max uses reached")

        # membership checks
        member = GroupMember.objects.filter(group=invite.group, user_id=user.sub).first()
        if member and member.status == "ACTIVE":
            return "ALREADY_GROUP_MEMBER"
        if member and member.status == "LEFT":
            # reactivate
            member.status = "ACTIVE"
            member.left_at = None
            member.save()
            GroupInviteRepository.increment_used(invite)
            invite.group.member_count = GroupMember.objects.filter(group=invite.group, status="ACTIVE").count()
            invite.group.save(update_fields=["member_count"])

            # publish events
            self.publisher.publish("GroupInviteAccepted", {"group_id": str(invite.group.id), "invite_id": str(invite.id), "user_id": user.sub}, "group.invite.accepted")
            self.publisher.publish("GroupMemberJoined", {"group_id": str(invite.group.id), "user_id": user.sub}, "group.member.joined")
            return "OK"

        if member and member.status == "REMOVED":
            raise PermissionError("removed users cannot rejoin")

        # create new member
        GroupMember.objects.create(
            group=invite.group,
            user_id=user.sub,
            phone_number=user.phone_number,
            display_name_snapshot=getattr(user, "display_name", None),
            role="MEMBER",
            status="ACTIVE",
        )

        GroupInviteRepository.increment_used(invite)
        invite.group.member_count = GroupMember.objects.filter(group=invite.group, status="ACTIVE").count()
        invite.group.save(update_fields=["member_count"])

        # publish events
        self.publisher.publish("GroupInviteAccepted", {"group_id": str(invite.group.id), "invite_id": str(invite.id), "user_id": user.sub}, "group.invite.accepted")
        self.publisher.publish("GroupMemberJoined", {"group_id": str(invite.group.id), "user_id": user.sub}, "group.member.joined")

        return "OK"


    def revoke_invite(self, invite, actor):
        # permission
        if not rules.is_owner_or_admin(invite.group, actor.sub):
            raise PermissionError("not allowed")

        GroupInviteRepository.revoke(invite)
        self.publisher.publish("GroupInviteRevoked", {"group_id": str(invite.group.id), "invite_id": str(invite.id), "revoked_by": actor.sub}, "group.invite.revoked")
        return invite
