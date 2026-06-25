import base64
import json
from datetime import timedelta

from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from apps.media_files.domain.models import (
    ExpenseProjection,
    ExpenseStatusChoices,
    GroupMemberProjection,
    GroupProjection,
    GroupStatusChoices,
    InboxMessage,
    InboxMessageStatusChoices,
    MediaAccessLog,
    MediaFile,
    MediaFileTypeChoices,
    MediaStatusChoices,
    OutboxMessage,
    OutboxMessageStatusChoices,
    UserProjection,
)


class UserProjectionRepository:
    @staticmethod
    def upsert_from_event(**data):
        identity_user_id = data.get("user_id") or data.get("identity_user_id")
        if not identity_user_id:
            return None
        defaults = {
            "email": data.get("email", ""),
            "art_name": data.get("art_name"),
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
    def _contact_snapshot(user_id, fallback=""):
        user = UserProjectionRepository.get(user_id)
        if user:
            return user.email, user.art_name
        return fallback, None

    @staticmethod
    def upsert_joined(**data):
        group_id = data.get("group_id")
        user_id = data.get("user_id")
        if not group_id or not user_id:
            return None
        email = data.get("email")
        art_name = data.get("art_name_snapshot") or data.get("art_name")
        if not email:
            email, fallback_display = GroupMemberProjectionRepository._contact_snapshot(user_id)
            art_name = art_name or fallback_display
        defaults = {
            "email": email or "",
            "art_name_snapshot": art_name,
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
            member = GroupMemberProjection(group_id=group_id, user_id=user_id, email=data.get("email", ""), role=data.get("role", "MEMBER"))
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
            member = GroupMemberProjection(group_id=group_id, user_id=user_id, email=data.get("email", ""), role=data.get("role", "MEMBER"))
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

    @staticmethod
    def list_active_group_ids_for_user(user_id):
        return list(
            GroupMemberProjection.objects.filter(
                user_id=user_id,
                status="ACTIVE",
                group_id__in=GroupProjection.objects.filter(status=GroupStatusChoices.ACTIVE).values("group_id"),
            ).values_list("group_id", flat=True)
        )


class ExpenseProjectionRepository:
    @staticmethod
    def get(expense_id):
        return ExpenseProjection.objects.filter(expense_id=expense_id).first()

    @staticmethod
    def upsert_from_event(*, event_id, event_type, occurred_at=None, **data):
        expense_id = data.get("expense_id")
        group_id = data.get("group_id")
        if not expense_id or not group_id:
            return None
        current = ExpenseProjection.objects.filter(expense_id=expense_id).first()
        version = int(data.get("version") or (current.version if current else 1) or 1)
        if current and current.last_event_id and str(current.last_event_id) == str(event_id):
            return current
        if current and event_type == "ExpenseUpdated" and version < current.version:
            return current
        if current and event_type == "ExpenseCreated" and current.version > 1:
            return current
        defaults = {
            "group_id": group_id,
            "status": data.get("status") or (current.status if current else ExpenseStatusChoices.ACTIVE),
            "payer_user_id": data.get("payer_user_id") or (current.payer_user_id if current else None),
            "created_by_user_id": data.get("created_by_user_id") or (current.created_by_user_id if current else None),
            "version": version,
            "last_event_id": event_id,
            "last_event_at": occurred_at,
        }
        obj, _ = ExpenseProjection.objects.update_or_create(expense_id=expense_id, defaults=defaults)
        return obj

    @staticmethod
    def mark_deleted(*, event_id, occurred_at=None, **data):
        expense_id = data.get("expense_id")
        group_id = data.get("group_id")
        if not expense_id or not group_id:
            return None
        current = ExpenseProjection.objects.filter(expense_id=expense_id).first()
        version = current.version if current else 1
        defaults = {
            "group_id": group_id,
            "status": data.get("status") or ExpenseStatusChoices.DELETED,
            "payer_user_id": current.payer_user_id if current else None,
            "created_by_user_id": current.created_by_user_id if current else None,
            "version": version,
            "last_event_id": event_id,
            "last_event_at": occurred_at,
        }
        obj, _ = ExpenseProjection.objects.update_or_create(expense_id=expense_id, defaults=defaults)
        return obj


class MediaFileRepository:
    MAX_PAGE_SIZE = 100

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
    def _receipt_queryset():
        return MediaFile.objects.filter(
            file_type=MediaFileTypeChoices.RECEIPT,
            status=MediaStatusChoices.ACTIVE,
        ).order_by("-created_at", "-id")

    @staticmethod
    def encode_cursor(row):
        payload = {"created_at": row.created_at.isoformat(), "id": str(row.id)}
        return base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8")

    @staticmethod
    def decode_cursor(cursor):
        try:
            payload = json.loads(base64.urlsafe_b64decode(cursor.encode("utf-8")).decode("utf-8"))
            return payload["created_at"], payload["id"]
        except Exception as exc:  # noqa: BLE001
            raise ValueError("Invalid cursor.") from exc

    @classmethod
    def _apply_cursor(cls, qs, cursor):
        if not cursor:
            return qs
        created_at, row_id = cls.decode_cursor(cursor)
        return qs.filter(Q(created_at__lt=created_at) | Q(created_at=created_at, id__lt=row_id))

    @classmethod
    def list_expense_receipts(cls, *, expense_id, group_id, cursor=None, page_size=20):
        safe_page_size = min(max(int(page_size or 20), 1), cls.MAX_PAGE_SIZE)
        qs = cls._receipt_queryset().filter(related_expense_id=expense_id, group_id=group_id)
        qs = cls._apply_cursor(qs, cursor)
        rows = list(qs[: safe_page_size + 1])
        next_cursor = None
        if len(rows) > safe_page_size:
            next_cursor = cls.encode_cursor(rows[safe_page_size - 1])
            rows = rows[:safe_page_size]
        return rows, next_cursor

    @classmethod
    def list_user_receipts(
        cls,
        *,
        user_id,
        active_group_ids,
        group_id=None,
        expense_id=None,
        uploaded_by_me=None,
        from_date=None,
        to_date=None,
        cursor=None,
        page_size=20,
    ):
        safe_page_size = min(max(int(page_size or 20), 1), cls.MAX_PAGE_SIZE)
        qs = cls._receipt_queryset().filter(group_id__in=active_group_ids)
        if group_id:
            qs = qs.filter(group_id=group_id)
        if expense_id:
            qs = qs.filter(related_expense_id=expense_id)
        if uploaded_by_me is True:
            qs = qs.filter(uploaded_by_user_id=user_id)
        if from_date:
            qs = qs.filter(created_at__gte=from_date)
        if to_date:
            qs = qs.filter(created_at__lte=to_date)
        qs = cls._apply_cursor(qs, cursor)
        rows = list(qs[: safe_page_size + 1])
        next_cursor = None
        if len(rows) > safe_page_size:
            next_cursor = cls.encode_cursor(rows[safe_page_size - 1])
            rows = rows[:safe_page_size]
        return rows, next_cursor

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

    @staticmethod
    def bulk_create_for_files(media_files, *, user_id, action, ip_address=None, user_agent=None):
        logs = [
            MediaAccessLog(
                media_file=media_file,
                user_id=user_id,
                action=action,
                ip_address=ip_address,
                user_agent=user_agent,
            )
            for media_file in media_files
        ]
        if logs:
            MediaAccessLog.objects.bulk_create(logs)
        return logs


class OutboxRepository:
    @staticmethod
    def create(*, event_type, routing_key, payload, exchange, source_service="media-service"):
        return OutboxMessage.objects.create(
            event_id=payload["event_id"],
            event_type=event_type,
            event_version=int(payload.get("event_version", 1)),
            source_service=source_service,
            exchange=exchange,
            routing_key=routing_key,
            payload=payload,
        )

    @staticmethod
    def pending(limit: int = 50, max_retry_count: int = 5):
        return OutboxMessage.objects.filter(
            status__in=[OutboxMessageStatusChoices.PENDING, OutboxMessageStatusChoices.FAILED],
            retry_count__lt=max_retry_count,
            available_at__lte=timezone.now(),
        ).order_by("created_at")[:limit]

    @staticmethod
    def mark_published(message):
        message.status = OutboxMessageStatusChoices.PUBLISHED
        message.published_at = timezone.now()
        message.last_error = None
        message.save(update_fields=["status", "published_at", "last_error", "updated_at"])

    @staticmethod
    def mark_failed(message, error: str):
        message.retry_count += 1
        message.last_error = error
        max_retry_count = int(getattr(settings, "EVENT_MAX_RETRY_COUNT", 5))
        retry_delays = [int(value.strip()) for value in str(getattr(settings, "EVENT_RETRY_DELAY_SECONDS", "10,30,60")).split(",") if value.strip()]
        if hasattr(message, "available_at") and message.retry_count <= len(retry_delays):
            message.available_at = timezone.now() + timedelta(seconds=retry_delays[message.retry_count - 1])
        if message.retry_count >= max_retry_count:
            message.status = OutboxMessageStatusChoices.FAILED
        else:
            message.status = OutboxMessageStatusChoices.PENDING
        update_fields = ["retry_count", "last_error", "status", "updated_at"]
        if hasattr(message, "available_at"):
            update_fields.append("available_at")
        message.save(update_fields=update_fields)


class InboxRepository:
    @staticmethod
    def was_processed(event_id):
        return InboxMessage.objects.filter(event_id=event_id, status=InboxMessageStatusChoices.PROCESSED).exists()

    @staticmethod
    def mark_processed(event_id, event_type, source_service, routing_key, payload):
        obj, _ = InboxMessage.objects.update_or_create(
            event_id=event_id,
            defaults={
                "event_type": event_type,
                "source_service": source_service,
                "routing_key": routing_key,
                "payload": payload,
                "status": InboxMessageStatusChoices.PROCESSED,
                "processed_at": timezone.now(),
                "error_message": None,
            },
        )
        return obj

    @staticmethod
    def mark_failed(event_id, event_type, source_service, routing_key, payload, error_message):
        obj, _ = InboxMessage.objects.update_or_create(
            event_id=event_id,
            defaults={
                "event_type": event_type,
                "source_service": source_service,
                "routing_key": routing_key,
                "payload": payload,
                "status": InboxMessageStatusChoices.FAILED,
                "processed_at": timezone.now(),
                "error_message": error_message,
            },
        )
        return obj

    @staticmethod
    def mark_skipped(event_id, event_type, source_service, routing_key, payload):
        obj, _ = InboxMessage.objects.update_or_create(
            event_id=event_id,
            defaults={
                "event_type": event_type,
                "source_service": source_service,
                "routing_key": routing_key,
                "payload": payload,
                "status": InboxMessageStatusChoices.SKIPPED,
                "processed_at": timezone.now(),
                "error_message": None,
            },
        )
        return obj
