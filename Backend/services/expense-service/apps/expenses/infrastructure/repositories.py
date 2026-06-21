"""Database repositories for expense-service."""

from __future__ import annotations

from datetime import timedelta
from typing import Optional

from django.db import transaction
from django.db.models import QuerySet
from django.conf import settings
from django.utils import timezone

from apps.expenses.domain.models import (
    Expense,
    ExpenseParticipant,
    GroupMemberProjection,
    GroupProjection,
    UserProjection,
)


class ProjectionRepository:
    """Read access for local identity/group projections."""

    @staticmethod
    def get_group(group_id: object) -> GroupProjection | None:
        return GroupProjection.objects.filter(group_id=group_id).first()

    @staticmethod
    def get_member(group_id: object, user_id: object) -> GroupMemberProjection | None:
        return GroupMemberProjection.objects.filter(group_id=group_id, user_id=user_id).first()

    @staticmethod
    def get_active_member(group_id: object, user_id: object) -> GroupMemberProjection | None:
        return GroupMemberProjection.objects.filter(
            group_id=group_id,
            user_id=user_id,
            status=GroupMemberProjection.STATUS_ACTIVE,
        ).first()

    @staticmethod
    def is_active_member(group_id: object, user_id: object) -> bool:
        return ProjectionRepository.get_active_member(group_id, user_id) is not None

    @staticmethod
    def get_user(identity_user_id: object) -> UserProjection | None:
        return UserProjection.objects.filter(identity_user_id=identity_user_id).first()


class ExpenseRepository:
    """Persistence helpers for expenses and participants."""

    @staticmethod
    def create_expense(**kwargs) -> Expense:
        return Expense.objects.create(**kwargs)

    @staticmethod
    def get_by_id(expense_id: object) -> Optional[Expense]:
        return Expense.objects.filter(id=expense_id).prefetch_related("participants").first()

    @staticmethod
    def list_by_group(
        group_id: object,
        filters: dict | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> list[Expense]:
        qs: QuerySet[Expense] = (
            Expense.objects.filter(group_id=group_id)
            .exclude(status=Expense.STATUS_DELETED)
            .prefetch_related("participants")
            .order_by("-created_at")
        )

        if filters:
            if filters.get("payer_user_id"):
                qs = qs.filter(payer_user_id=filters["payer_user_id"])
            if filters.get("created_by_user_id"):
                qs = qs.filter(created_by_user_id=filters["created_by_user_id"])
            if filters.get("from_date"):
                qs = qs.filter(expense_date__gte=filters["from_date"])
            if filters.get("to_date"):
                qs = qs.filter(expense_date__lte=filters["to_date"])

        safe_page = max(int(page), 1)
        safe_page_size = min(max(int(page_size), 1), 100)
        start = (safe_page - 1) * safe_page_size
        end = start + safe_page_size
        return list(qs[start:end])

    @staticmethod
    def update_expense(expense: Expense, **kwargs) -> Expense:
        for key, value in kwargs.items():
            setattr(expense, key, value)
        expense.save()
        return expense

    @staticmethod
    def soft_delete(expense: Expense) -> Expense:
        expense.status = Expense.STATUS_DELETED
        expense.deleted_at = timezone.now()
        expense.save(update_fields=["status", "deleted_at", "updated_at"])
        return expense

    @staticmethod
    @transaction.atomic
    def add_participants(expense: Expense, participants: list[dict]) -> list[ExpenseParticipant]:
        return [ExpenseParticipant.objects.create(expense=expense, **row) for row in participants]

    @staticmethod
    @transaction.atomic
    def replace_participants(expense: Expense, participants: list[dict]) -> list[ExpenseParticipant]:
        expense.participants.all().delete()
        return ExpenseRepository.add_participants(expense, participants)


from django.conf import settings
from django.utils import timezone
from apps.expenses.domain.models import (
    InboxMessage,
    InboxMessageStatusChoices,
    OutboxMessage,
    OutboxMessageStatusChoices,
)


class OutboxRepository:
    @staticmethod
    def create(*, event_type, routing_key, payload, exchange, source_service="expense-service"):
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

