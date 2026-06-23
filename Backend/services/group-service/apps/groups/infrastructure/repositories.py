"""Database repositories for group-service."""

from __future__ import annotations

from datetime import timedelta
from typing import Optional

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.groups.domain.models import (
    Group,
    GroupInvite,
    GroupMember,
    InboxMessage,
    InboxMessageStatusChoices,
    OutboxMessage,
    OutboxMessageStatusChoices,
    UserProjection,
)


class UserProjectionRepository:
    @staticmethod
    def get_by_identity_id(identity_user_id):
        return UserProjection.objects.filter(identity_user_id=identity_user_id).first()

    @staticmethod
    def get_map_by_identity_ids(identity_user_ids):
        projection_ids = {identity_user_id for identity_user_id in identity_user_ids if identity_user_id}
        if not projection_ids:
            return {}
        projections = UserProjection.objects.filter(identity_user_id__in=projection_ids)
        return {str(projection.identity_user_id): projection for projection in projections}

    @staticmethod
    def create_or_update(
        identity_user_id,
        email,
        art_name=None,
        first_name=None,
        last_name=None,
        role=None,
        is_active=True,
    ):
        obj, _ = UserProjection.objects.update_or_create(
            identity_user_id=identity_user_id,
            defaults={
                "email": email,
                "art_name": art_name,
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
    def add_owner(group: Group, user_id, email, art_name):
        member = GroupMember.objects.create(
            group=group,
            user_id=user_id,
            email=email,
            art_name_snapshot=art_name,
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
        invite.status = "REVOKED"
        invite.revoked_at = timezone.now()
        invite.save(update_fields=["status", "revoked_at"])
        return invite


class OutboxRepository:
    @staticmethod
    def create(*, event_type, routing_key, payload, exchange, source_service="group-service"):
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
        retry_delays = [
            int(value.strip())
            for value in str(getattr(settings, "EVENT_RETRY_DELAY_SECONDS", "10,30,60")).split(",")
            if value.strip()
        ]
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
        return InboxMessage.objects.filter(
            event_id=event_id,
            status=InboxMessageStatusChoices.PROCESSED,
        ).exists()

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
