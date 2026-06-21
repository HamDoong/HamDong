from apps.media_files.domain.models import GroupMemberProjection, GroupProjection, MediaFile, MediaStatusChoices


def is_active_group(group_id) -> bool:
    return GroupProjection.objects.filter(group_id=group_id, status="ACTIVE").exists()


def is_active_member(group_id, user_id) -> bool:
    return GroupMemberProjection.objects.filter(group_id=group_id, user_id=user_id, status="ACTIVE").exists()


def is_owner_or_admin(group_id, user_id) -> bool:
    return GroupMemberProjection.objects.filter(group_id=group_id, user_id=user_id, status="ACTIVE", role__in=("OWNER", "ADMIN")).exists()


def can_access_media(media_file: MediaFile, user_id) -> bool:
    return media_file.status == MediaStatusChoices.ACTIVE and is_active_group(media_file.group_id) and is_active_member(media_file.group_id, user_id)


def can_manage_media(media_file: MediaFile, user_id) -> bool:
    return media_file.uploaded_by_user_id == user_id or is_owner_or_admin(media_file.group_id, user_id)
