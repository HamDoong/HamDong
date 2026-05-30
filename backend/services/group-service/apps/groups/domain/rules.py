"""Domain permission rules for groups."""

from apps.groups.domain.models import GroupMember


def is_active_member(group, user_id) -> bool:
    return GroupMember.objects.filter(group=group, user_id=user_id, status="ACTIVE").exists()


def is_owner(group, user_id) -> bool:
    return GroupMember.objects.filter(group=group, user_id=user_id, role="OWNER", status="ACTIVE").exists()


def is_owner_or_admin(group, user_id) -> bool:
    return GroupMember.objects.filter(group=group, user_id=user_id, role__in=("OWNER", "ADMIN"), status="ACTIVE").exists()
"""Domain rules for group-service."""
