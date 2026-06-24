from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone as dt_timezone

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.dashboard.domain.models import (
    DashboardActivity,
    GroupMemberProjection,
    GroupMemberRoleChoices,
    GroupMemberStatusChoices,
    GroupProjection,
    GroupStatusChoices,
    InboxMessage,
    InboxMessageStatusChoices,
    UserProjection,
)


def normalize_uuid(value):
    if value in (None, ""):
        return None
    if isinstance(value, uuid.UUID):
        return value
    return uuid.UUID(str(value))


@dataclass(frozen=True)
class ActivityFeedRecord:
    id: uuid.UUID
    event_type: str
    group_id: uuid.UUID
    actor_user_id: uuid.UUID | None
    occurred_at: datetime
    summary: dict
    source_service: str
    source_object_id: uuid.UUID | None


class UserProjectionRepository:
    @staticmethod
    def upsert_from_event(**data):
        identity_user_id = normalize_uuid(data.get("user_id") or data.get("identity_user_id"))
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
        obj, _ = UserProjection.objects.update_or_create(
            identity_user_id=identity_user_id,
            defaults=defaults,
        )
        GroupMemberProjection.objects.filter(user_id=identity_user_id).update(
            email=obj.email,
            art_name_snapshot=obj.art_name,
        )
        return obj

    @staticmethod
    def get(identity_user_id):
        return UserProjection.objects.filter(identity_user_id=normalize_uuid(identity_user_id)).first()


class GroupProjectionRepository:
    @staticmethod
    def upsert_from_event(**data):
        group_id = normalize_uuid(data.get("group_id"))
        if not group_id:
            return None
        defaults = {
            "title": data.get("title") or "",
            "description": data.get("description") or "",
            "group_type": data.get("group_type") or "GENERAL",
            "status": data.get("status") or GroupStatusChoices.ACTIVE,
            "created_by_user_id": normalize_uuid(data.get("created_by_user_id")),
            "member_count": int(data.get("member_count") or 0),
        }
        obj, _ = GroupProjection.objects.update_or_create(group_id=group_id, defaults=defaults)
        return obj

    @staticmethod
    def get(group_id):
        return GroupProjection.objects.filter(group_id=normalize_uuid(group_id)).first()


class GroupMemberProjectionRepository:
    @staticmethod
    def upsert_joined(**data):
        group_id = normalize_uuid(data.get("group_id"))
        user_id = normalize_uuid(data.get("user_id"))
        if not group_id or not user_id:
            return None
        defaults = {
            "email": data.get("email", ""),
            "art_name_snapshot": data.get("art_name"),
            "role": data.get("role") or GroupMemberRoleChoices.MEMBER,
            "status": data.get("status") or GroupMemberStatusChoices.ACTIVE,
        }
        obj, _ = GroupMemberProjection.objects.update_or_create(
            group_id=group_id,
            user_id=user_id,
            defaults=defaults,
        )
        return obj

    @staticmethod
    def mark_removed(**data):
        group_id = normalize_uuid(data.get("group_id"))
        user_id = normalize_uuid(data.get("user_id"))
        if not group_id or not user_id:
            return None
        return GroupMemberProjection.objects.filter(group_id=group_id, user_id=user_id).update(
            status=GroupMemberStatusChoices.REMOVED
        )

    @staticmethod
    def mark_left(**data):
        group_id = normalize_uuid(data.get("group_id"))
        user_id = normalize_uuid(data.get("user_id") or data.get("left_by_user_id"))
        if not group_id or not user_id:
            return None
        return GroupMemberProjection.objects.filter(group_id=group_id, user_id=user_id).update(
            status=GroupMemberStatusChoices.LEFT
        )

    @staticmethod
    def list_active_group_ids_for_user(user_id):
        return list(
            GroupMemberProjection.objects.filter(
                user_id=normalize_uuid(user_id),
                status=GroupMemberStatusChoices.ACTIVE,
            ).values_list("group_id", flat=True)
        )

    @staticmethod
    def get(group_id, user_id):
        return GroupMemberProjection.objects.filter(
            group_id=normalize_uuid(group_id),
            user_id=normalize_uuid(user_id),
        ).first()


class ActivityRepository:
    MAX_LIMIT = 100

    @staticmethod
    def create_if_missing(
        *,
        event_id,
        event_type,
        source_service,
        routing_key,
        group_id,
        actor_user_id,
        source_object_id,
        summary,
        occurred_at,
    ):
        activity, _ = DashboardActivity.objects.get_or_create(
            id=normalize_uuid(event_id),
            defaults={
                "event_type": event_type,
                "source_service": source_service,
                "routing_key": routing_key,
                "group_id": normalize_uuid(group_id),
                "actor_user_id": normalize_uuid(actor_user_id),
                "source_object_id": normalize_uuid(source_object_id),
                "summary": summary or {},
                "occurred_at": occurred_at,
            },
        )
        return activity

    @staticmethod
    def encode_cursor(row: DashboardActivity) -> str:
        return f"{row.occurred_at.isoformat()}|{row.id}"

    @staticmethod
    def decode_cursor(value: str):
        try:
            occurred_at_raw, item_id = str(value).split("|", 1)
            return {
                "occurred_at": datetime.fromisoformat(occurred_at_raw),
                "id": normalize_uuid(item_id),
            }
        except Exception as exc:
            raise ValueError("INVALID_CURSOR") from exc

    @staticmethod
    def list_for_user(user_id, *, group_id=None, event_type=None, from_date=None, to_date=None, cursor=None, page_size=20):
        active_group_ids = GroupMemberProjectionRepository.list_active_group_ids_for_user(user_id)
        if not active_group_ids:
            return [], None

        qs = DashboardActivity.objects.filter(group_id__in=active_group_ids).order_by("-occurred_at", "-id")
        if group_id:
            group_id = normalize_uuid(group_id)
            if group_id not in active_group_ids:
                return [], None
            qs = qs.filter(group_id=group_id)
        if event_type:
            qs = qs.filter(event_type=event_type)
        if from_date:
            qs = qs.filter(occurred_at__gte=datetime.combine(from_date, time.min, tzinfo=dt_timezone.utc))
        if to_date:
            qs = qs.filter(occurred_at__lt=datetime.combine(to_date + timedelta(days=1), time.min, tzinfo=dt_timezone.utc))
        if cursor:
            cursor_data = ActivityRepository.decode_cursor(cursor)
            qs = qs.filter(
                Q(occurred_at__lt=cursor_data["occurred_at"])
                | Q(occurred_at=cursor_data["occurred_at"], id__lt=cursor_data["id"])
            )

        safe_limit = min(max(int(page_size or 20), 1), ActivityRepository.MAX_LIMIT)
        rows = list(qs[: safe_limit + 1])
        next_cursor = None
        if len(rows) > safe_limit:
            next_cursor = ActivityRepository.encode_cursor(rows[safe_limit - 1])
            rows = rows[:safe_limit]

        return [
            ActivityFeedRecord(
                id=row.id,
                event_type=row.event_type,
                group_id=row.group_id,
                actor_user_id=row.actor_user_id,
                occurred_at=row.occurred_at,
                summary=row.summary or {},
                source_service=row.source_service,
                source_object_id=row.source_object_id,
            )
            for row in rows
        ], next_cursor


class InboxRepository:
    @staticmethod
    def was_processed(event_id) -> bool:
        return InboxMessage.objects.filter(
            event_id=normalize_uuid(event_id),
            status__in=[InboxMessageStatusChoices.PROCESSED, InboxMessageStatusChoices.SKIPPED],
        ).exists()

    @staticmethod
    @transaction.atomic
    def mark_processed(event_id, event_type, source_service, routing_key, payload):
        InboxMessage.objects.update_or_create(
            event_id=normalize_uuid(event_id),
            defaults={
                "event_type": event_type,
                "source_service": source_service,
                "routing_key": routing_key,
                "payload": payload or {},
                "status": InboxMessageStatusChoices.PROCESSED,
                "processed_at": timezone.now(),
                "error_message": "",
            },
        )

    @staticmethod
    @transaction.atomic
    def mark_skipped(event_id, event_type, source_service, routing_key, payload):
        InboxMessage.objects.get_or_create(
            event_id=normalize_uuid(event_id),
            defaults={
                "event_type": event_type,
                "source_service": source_service,
                "routing_key": routing_key,
                "payload": payload or {},
                "status": InboxMessageStatusChoices.SKIPPED,
                "processed_at": timezone.now(),
                "error_message": "",
            },
        )

    @staticmethod
    @transaction.atomic
    def mark_failed(event_id, event_type, source_service, routing_key, payload, error_message):
        InboxMessage.objects.update_or_create(
            event_id=normalize_uuid(event_id),
            defaults={
                "event_type": event_type,
                "source_service": source_service,
                "routing_key": routing_key,
                "payload": payload or {},
                "status": InboxMessageStatusChoices.FAILED,
                "processed_at": timezone.now(),
                "error_message": error_message[:2000],
            },
        )
