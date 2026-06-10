"""Domain rules for group-service."""

from apps.groups.domain.models import GroupMember


def is_active_member(group, user_id) -> bool:
    return GroupMember.objects.filter(group=group, user_id=user_id, status="ACTIVE").exists()


def is_owner(group, user_id) -> bool:
    return GroupMember.objects.filter(group=group, user_id=user_id, role="OWNER", status="ACTIVE").exists()


def is_owner_or_admin(group, user_id) -> bool:
    return GroupMember.objects.filter(group=group, user_id=user_id, role__in=("OWNER", "ADMIN"), status="ACTIVE").exists()


def normalize_title_parts(title_parts):
    if title_parts is None:
        return None
    normalized = []
    for part in title_parts:
        if not isinstance(part, str):
            raise ValueError("INVALID_GROUP_TITLE_PARTS")
        stripped = part.strip()
        if not stripped:
            raise ValueError("INVALID_GROUP_TITLE_PARTS")
        normalized.append(stripped)
    if not normalized:
        raise ValueError("INVALID_GROUP_TITLE_PARTS")
    return normalized
