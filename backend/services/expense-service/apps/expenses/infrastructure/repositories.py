from typing import Optional

from django.db import transaction

from apps.expenses.domain.models import (
    Expense,
    ExpenseParticipant,
    GroupMemberProjection,
    GroupProjection,
    UserProjection,
)


class ProjectionRepository:
    @staticmethod
    def get_group(group_id):
        return GroupProjection.objects.filter(group_id=group_id).first()

    @staticmethod
    def is_active_member(group_id, user_id) -> bool:
        return GroupMemberProjection.objects.filter(
            group_id=group_id,
            user_id=user_id,
            status=GroupMemberProjection.STATUS_ACTIVE,
        ).exists()

    @staticmethod
    def get_member(group_id, user_id, *, active_only: bool = False):
        queryset = GroupMemberProjection.objects.filter(group_id=group_id, user_id=user_id)
        if active_only:
            queryset = queryset.filter(status=GroupMemberProjection.STATUS_ACTIVE)
        return queryset.first()

    @staticmethod
    def get_active_members_map(group_id, user_ids):
        queryset = GroupMemberProjection.objects.filter(
            group_id=group_id,
            user_id__in=list(user_ids),
            status=GroupMemberProjection.STATUS_ACTIVE,
        )
        return {str(member.user_id): member for member in queryset}

    @staticmethod
    def get_user_projection(identity_user_id):
        return UserProjection.objects.filter(identity_user_id=identity_user_id).first()


class ExpenseRepository:
    @staticmethod
    def create_expense(**kwargs) -> Expense:
        return Expense.objects.create(**kwargs)

    @staticmethod
    def get_by_id(expense_id) -> Optional[Expense]:
        return Expense.objects.prefetch_related("participants").filter(id=expense_id).first()

    @staticmethod
    def list_by_group(group_id, filters: dict | None = None, page: int = 1, page_size: int = 50):
        queryset = (
            Expense.objects.prefetch_related("participants")
            .filter(group_id=group_id)
            .exclude(status=Expense.STATUS_DELETED)
            .order_by("-created_at")
        )

        if filters:
            if filters.get("payer_user_id"):
                queryset = queryset.filter(payer_user_id=filters["payer_user_id"])
            if filters.get("created_by_user_id"):
                queryset = queryset.filter(created_by_user_id=filters["created_by_user_id"])
            if filters.get("from_date"):
                queryset = queryset.filter(created_at__gte=filters["from_date"])
            if filters.get("to_date"):
                queryset = queryset.filter(created_at__lte=filters["to_date"])

        start = max(page - 1, 0) * page_size
        end = start + page_size
        return list(queryset[start:end])

    @staticmethod
    def update_expense(expense: Expense, **kwargs) -> Expense:
        for key, value in kwargs.items():
            setattr(expense, key, value)
        expense.save()
        return expense

    @staticmethod
    def soft_delete(expense: Expense) -> Expense:
        expense.status = Expense.STATUS_DELETED
        expense.save(update_fields=["status", "deleted_at", "updated_at", "version"])
        return expense

    @staticmethod
    @transaction.atomic
    def add_participants(expense: Expense, participants: list[dict]) -> list[ExpenseParticipant]:
        participant_objects = [
            ExpenseParticipant(expense=expense, **participant) for participant in participants
        ]
        ExpenseParticipant.objects.bulk_create(participant_objects)
        return participant_objects

    @staticmethod
    @transaction.atomic
    def replace_participants(expense: Expense, participants: list[dict]) -> list[ExpenseParticipant]:
        expense.participants.all().delete()
        return ExpenseRepository.add_participants(expense, participants)
