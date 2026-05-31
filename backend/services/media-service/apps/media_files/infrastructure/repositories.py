from django.utils import timezone

from apps.media_files.domain.models import GroupMemberProjection, GroupProjection, MediaAccessLog, MediaFile, MediaStatusChoices, UserProjection


class UserProjectionRepository:
    @staticmethod
    def upsert_from_event(**data):
        identity_user_id = data.get("user_id") or data.get("identity_user_id")
        if not identity_user_id:
            return None
        defaults = {
            "phone_number": data.get("phone_number", ""),
            "display_name": data.get("display_name"),
            "first_name": data.get("first_name"),
            "last_name": data.get("last_name"),
            "role": data.get("role", "USER"),
            "is_active": data.get("is_active", True),
        }
        obj, _ = UserProjection.objects.update_or_create(identity_user_id=identity_user_id, defaults=defaults)
        return obj

    @staticmethod
    def get(identity_user_id):
        return UserProjection.objects.filter(identity_user_id=identity_user_id).first()


class GroupProjectionRepository:
    @staticmethod
    def upsert_from_event(**data):
        group_id = data.get("group_id")
        if not group_id:
            return None
        current = GroupProjection.objects.filter(group_id=group_id).first()
        defaults = {
            "title": data.get("title") or (current.title if current else "Untitled group"),
            "group_type": data.get("group_type") or (current.group_type if current else "GENERAL"),
            "status": data.get("status") or (current.status if current else "ACTIVE"),
            "created_by_user_id": data.get("created_by_user_id") or data.get("created_by") or (current.created_by_user_id if current else group_id),
            "member_count": data.get("member_count") if data.get("member_count") is not None else (current.member_count if current else 1),
        }
        obj, _ = GroupProjection.objects.update_or_create(group_id=group_id, defaults=defaults)
        return obj

    @staticmethod
    def get(group_id):
        return GroupProjection.objects.filter(group_id=group_id).first()

    @staticmethod
    def refresh_member_count(group_id):
        group = GroupProjection.objects.filter(group_id=group_id).first()
        if not group:
            return None
        group.member_count = GroupMemberProjection.objects.filter(group_id=group_id, status="ACTIVE").count()
        group.save(update_fields=["member_count", "updated_at"])
        return group


class GroupMemberProjectionRepository:
    @staticmethod
    def _phone_snapshot(user_id, fallback=""):
        user = UserProjectionRepository.get(user_id)
        if user:
            return user.phone_number, user.display_name
        return fallback, None

    @staticmethod
    def upsert_joined(**data):
        group_id = data.get("group_id")
        user_id = data.get("user_id")
        if not group_id or not user_id:
            return None
        phone_number = data.get("phone_number")
        display_name = data.get("display_name_snapshot") or data.get("display_name")
        if not phone_number:
            phone_number, fallback_display = GroupMemberProjectionRepository._phone_snapshot(user_id)
            display_name = display_name or fallback_display
        defaults = {
            "phone_number": phone_number or "",
            "display_name_snapshot": display_name,
            "role": data.get("role", "MEMBER"),
            "status": "ACTIVE",
            "joined_at": timezone.now(),
            "left_at": None,
            "removed_at": None,
        }
        obj, _ = GroupMemberProjection.objects.update_or_create(group_id=group_id, user_id=user_id, defaults=defaults)
        GroupProjectionRepository.refresh_member_count(group_id)
        return obj

    @staticmethod
    def mark_left(**data):
        group_id = data.get("group_id")
        user_id = data.get("user_id") or data.get("member_user_id")
        if not group_id or not user_id:
            return None
        member = GroupMemberProjection.objects.filter(group_id=group_id, user_id=user_id).first()
        if not member:
            member = GroupMemberProjection(group_id=group_id, user_id=user_id, phone_number=data.get("phone_number", ""), role=data.get("role", "MEMBER"))
        member.status = "LEFT"
        member.left_at = timezone.now()
        member.removed_at = None
        member.save()
        GroupProjectionRepository.refresh_member_count(group_id)
        return member

    @staticmethod
    def mark_removed(**data):
        group_id = data.get("group_id")
        user_id = data.get("user_id") or data.get("member_user_id")
        if not group_id or not user_id:
            return None
        member = GroupMemberProjection.objects.filter(group_id=group_id, user_id=user_id).first()
        if not member:
            member = GroupMemberProjection(group_id=group_id, user_id=user_id, phone_number=data.get("phone_number", ""), role=data.get("role", "MEMBER"))
        member.status = "REMOVED"
        member.removed_at = timezone.now()
        member.left_at = None
        member.save()
        GroupProjectionRepository.refresh_member_count(group_id)
        return member

    @staticmethod
    def get_active_member(group_id, user_id):
        return GroupMemberProjection.objects.filter(group_id=group_id, user_id=user_id, status="ACTIVE").first()

    @staticmethod
    def get(group_id, user_id):
        return GroupMemberProjection.objects.filter(group_id=group_id, user_id=user_id).first()


class MediaFileRepository:
    @staticmethod
    def create(**data):
        return MediaFile.objects.create(**data)

    @staticmethod
    def get(media_file_id):
        return MediaFile.objects.filter(id=media_file_id).first()

    @staticmethod
    def list_group_media(group_id, file_type=None, page=1, page_size=20):
        qs = MediaFile.objects.filter(group_id=group_id, status=MediaStatusChoices.ACTIVE).order_by("-created_at")
        if file_type:
            qs = qs.filter(file_type=file_type)
        return qs[(page - 1) * page_size : page * page_size], qs.count()

    @staticmethod
    def soft_delete(media_file: MediaFile):
        media_file.status = MediaStatusChoices.DELETED
        media_file.deleted_at = timezone.now()
        media_file.version += 1
        media_file.save(update_fields=["status", "deleted_at", "version", "updated_at"])
        return media_file


class MediaAccessLogRepository:
    @staticmethod
    def create(media_file, user_id, action, ip_address=None, user_agent=None):
        return MediaAccessLog.objects.create(media_file=media_file, user_id=user_id, action=action, ip_address=ip_address, user_agent=user_agent)
