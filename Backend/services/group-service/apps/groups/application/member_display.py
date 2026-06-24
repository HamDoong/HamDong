"""Helpers for resolving safe group member display names."""

from __future__ import annotations

from apps.groups.domain.models import GroupMember, UserProjection

SAFE_MEMBER_ART_NAME_FALLBACK = "عضو گروه"


def _clean_text(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def resolve_user_art_name(user, projection: UserProjection | None = None) -> str | None:
    return _clean_text(getattr(projection, "art_name", None)) or _clean_text(getattr(user, "art_name", None))


def resolve_member_art_name(member: GroupMember, projection: UserProjection | None = None) -> str:
    return (
        _clean_text(getattr(projection, "art_name", None))
        or _clean_text(member.art_name_snapshot)
        or SAFE_MEMBER_ART_NAME_FALLBACK
    )


def build_member_payload(
    member: GroupMember,
    *,
    projection: UserProjection | None = None,
    masked_email: str | None = None,
) -> dict:
    art_name = resolve_member_art_name(member, projection=projection)
    return {
        "id": member.id,
        "user_id": member.user_id,
        "art_name": art_name,
        "username": art_name,
        "art_name_snapshot": member.art_name_snapshot,
        "role": member.role,
        "joined_at": member.joined_at,
        "email": masked_email,
    }
