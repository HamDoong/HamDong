"""Database repositories for group-service."""

from typing import Optional
from django.db import transaction
from apps.groups.domain.models import (
	UserProjection,
	Group,
	GroupMember,
	GroupInvite,
)


class UserProjectionRepository:
	@staticmethod
	def get_by_identity_id(identity_user_id):
		return UserProjection.objects.filter(identity_user_id=identity_user_id).first()

	@staticmethod
	def create_or_update(identity_user_id, phone_number, display_name=None, first_name=None, last_name=None, role=None, is_active=True):
		obj, _ = UserProjection.objects.update_or_create(
			identity_user_id=identity_user_id,
			defaults={
				"phone_number": phone_number,
				"display_name": display_name,
				"first_name": first_name,
				"last_name": last_name,
				"role": role or "USER",
				"is_active": is_active,
			},
		)
		return obj


class GroupRepository:
	@staticmethod
	def create(**kwargs) -> Group:
		return Group.objects.create(**kwargs)

	@staticmethod
	def get_by_id(group_id) -> Optional[Group]:
		return Group.objects.filter(id=group_id).first()


class GroupMemberRepository:
	@staticmethod
	@transaction.atomic
	def add_owner(group: Group, user_id, phone_number, display_name):
		member = GroupMember.objects.create(
			group=group,
			user_id=user_id,
			phone_number=phone_number,
			display_name_snapshot=display_name,
			role="OWNER",
			status="ACTIVE",
		)
		group.member_count = GroupMember.objects.filter(group=group, status="ACTIVE").count()
		group.save(update_fields=["member_count"])
		return member

	@staticmethod
	def is_active_member(group: Group, user_id) -> bool:
		return GroupMember.objects.filter(group=group, user_id=user_id, status="ACTIVE").exists()


class GroupInviteRepository:
	@staticmethod
	def create(**kwargs) -> GroupInvite:
		return GroupInvite.objects.create(**kwargs)

	@staticmethod
	def get_by_token_hash(token_hash) -> Optional[GroupInvite]:
		return GroupInvite.objects.filter(token_hash=token_hash).first()

	@staticmethod
	def get_by_id(invite_id) -> Optional[GroupInvite]:
		return GroupInvite.objects.filter(id=invite_id).first()

	@staticmethod
	def increment_used(invite: GroupInvite) -> GroupInvite:
		invite.used_count = (invite.used_count or 0) + 1
		invite.save(update_fields=["used_count"])
		return invite

	@staticmethod
	def revoke(invite: GroupInvite) -> GroupInvite:
		from django.utils import timezone

		invite.status = "REVOKED"
		invite.revoked_at = timezone.now()
		invite.save(update_fields=["status", "revoked_at"])
		return invite

