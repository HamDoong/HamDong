from typing import Optional
from django.db import transaction
from apps.expenses.domain.models import (
    UserProjection,
    GroupProjection,
    GroupMemberProjection,
    Expense,
    ExpenseParticipant,
)


class ProjectionRepository:
    @staticmethod
    def get_group(group_id):
        return GroupProjection.objects.filter(group_id=group_id).first()

    @staticmethod
    def is_active_member(group_id, user_id) -> bool:
        return GroupMemberProjection.objects.filter(group_id=group_id, user_id=user_id, status="ACTIVE").exists()

    @staticmethod
    def get_member(group_id, user_id):
        return GroupMemberProjection.objects.filter(group_id=group_id, user_id=user_id).first()


class ExpenseRepository:
    @staticmethod
    def create_expense(**kwargs) -> Expense:
        return Expense.objects.create(**kwargs)

    @staticmethod
    def get_by_id(expense_id) -> Optional[Expense]:
        return Expense.objects.filter(id=expense_id).first()

    @staticmethod
    def list_by_group(group_id, filters: dict = None, page: int = 1, page_size: int = 50):
        qs = Expense.objects.filter(group_id=group_id).exclude(status="DELETED").order_by("-created_at")
        if filters:
            if filters.get("payer_user_id"):
                qs = qs.filter(payer_user_id=filters["payer_user_id"])
            if filters.get("created_by_user_id"):
                qs = qs.filter(created_by_user_id=filters["created_by_user_id"])
            if filters.get("from_date"):
                qs = qs.filter(created_at__gte=filters["from_date"])
            if filters.get("to_date"):
                qs = qs.filter(created_at__lte=filters["to_date"])
        start = (page - 1) * page_size
        end = start + page_size
        return list(qs[start:end])

    @staticmethod
    def update_expense(expense: Expense, **kwargs) -> Expense:
        for k, v in kwargs.items():
            setattr(expense, k, v)
        expense.save()
        return expense

    @staticmethod
    def soft_delete(expense: Expense):
        expense.status = "DELETED"
        from django.utils import timezone

        expense.deleted_at = timezone.now()
        expense.save()
        return expense

    @staticmethod
    @transaction.atomic
    def add_participants(expense: Expense, participants: list):
        objs = []
        for p in participants:
            objs.append(ExpenseParticipant.objects.create(expense=expense, **p))
        return objs
"""Database repositories for expense-service."""
