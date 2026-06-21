"""Use case orchestration for expense-service."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from uuid import UUID

from django.db import transaction
from django.utils import timezone

from apps.expenses.application.split_calculator import INVALID_SPLIT_AMOUNT, custom_split, equal_split
from apps.expenses.application.tax_calculator import (
    calculate_service_fee_amount_minor,
    calculate_tax_amount_minor,
    distribute_proportional,
)
from apps.expenses.domain.events import (
    expense_created_event,
    expense_deleted_event,
    expense_updated_event,
)
from apps.expenses.domain.models import Expense, GroupMemberProjection, GroupProjection
from apps.expenses.infrastructure.rabbitmq_publisher import RabbitMQPublisher
from apps.expenses.infrastructure.repositories import ExpenseRepository, ProjectionRepository


@dataclass
class ExpenseServiceError(ValueError):
    """Expected business-rule error."""

    code: str
    message: str

    def __str__(self) -> str:
        return self.code


@dataclass
class ExpensePermissionError(PermissionError):
    """Expected permission error."""

    code: str
    message: str

    def __str__(self) -> str:
        return self.code


class ExpenseService:
    """Application service for expense workflows."""

    def __init__(self, publisher: RabbitMQPublisher | None = None):
        self.publisher = publisher or RabbitMQPublisher()

    def create_expense(self, group_id: object, creator: Any, payload: dict[str, Any]) -> Expense:
        creator_user_id = self._request_user_id(creator)
        group = self._require_active_group(group_id)
        self._require_active_member(group.group_id, creator_user_id, error_code="NOT_GROUP_MEMBER")

        title = self._validated_title(payload.get("title"))
        currency = self._validated_currency(payload.get("currency", "IRR"))
        payer_user_id = payload.get("payer_user_id")
        payer_member = self._require_active_member(
            group.group_id,
            payer_user_id,
            error_code="PAYER_NOT_GROUP_MEMBER",
        )

        base_amount_minor = self._positive_amount(payload.get("base_amount_minor"))
        split_method = payload.get("split_method")

        base_shares = self._calculate_base_shares(split_method, payload, base_amount_minor)
        member_snapshots = self._require_active_participants(group.group_id, base_shares)

        tax_type = payload.get("tax_type", Expense.TAX_NONE)
        service_fee_type = payload.get("service_fee_type", Expense.SERVICE_NONE)

        tax_amount_minor = calculate_tax_amount_minor(
            tax_type,
            base_amount_minor,
            tax_percentage=payload.get("tax_percentage"),
            tax_amount_minor=payload.get("tax_amount_minor"),
        )
        service_fee_amount_minor = calculate_service_fee_amount_minor(
            service_fee_type,
            base_amount_minor,
            service_fee_percentage=payload.get("service_fee_percentage"),
            service_fee_amount_minor=payload.get("service_fee_amount_minor"),
        )
        total_amount_minor = base_amount_minor + tax_amount_minor + service_fee_amount_minor

        tax_shares = distribute_proportional(tax_amount_minor, base_shares)
        service_fee_shares = distribute_proportional(service_fee_amount_minor, base_shares)
        participants = self._build_participants(
            base_shares,
            tax_shares,
            service_fee_shares,
            member_snapshots,
        )
        self._verify_totals(participants, total_amount_minor)

        with transaction.atomic():
            expense = ExpenseRepository.create_expense(
                group_id=group.group_id,
                created_by_user_id=creator_user_id,
                payer_user_id=payer_member.user_id,
                title=title,
                description=payload.get("description") or None,
                currency=currency,
                base_amount_minor=base_amount_minor,
                tax_type=tax_type,
                tax_percentage=payload.get("tax_percentage") if tax_type == Expense.TAX_PERCENTAGE else None,
                tax_amount_minor=tax_amount_minor,
                service_fee_type=service_fee_type,
                service_fee_percentage=(
                    payload.get("service_fee_percentage")
                    if service_fee_type == Expense.SERVICE_PERCENTAGE
                    else None
                ),
                service_fee_amount_minor=service_fee_amount_minor,
                total_amount_minor=total_amount_minor,
                split_method=split_method,
                receipt_file_id=payload.get("receipt_file_id"),
                receipt_url=payload.get("receipt_url"),
                expense_date=payload.get("expense_date") or timezone.now(),
            )
            ExpenseRepository.add_participants(expense, participants)

        event = expense_created_event(expense, participants)
        self._publish(event)
        return ExpenseRepository.get_by_id(expense.id) or expense

    def list_expenses(
        self,
        group_id: object,
        requester: Any,
        filters: dict[str, Any] | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> list[Expense]:
        requester_user_id = self._request_user_id(requester)
        group = self._require_active_group(group_id)
        self._require_active_member(group.group_id, requester_user_id, error_code="NOT_GROUP_MEMBER")
        return ExpenseRepository.list_by_group(group.group_id, filters=filters, page=page, page_size=page_size)

    def get_expense(self, expense_id: object, requester: Any) -> Expense:
        requester_user_id = self._request_user_id(requester)
        expense = ExpenseRepository.get_by_id(expense_id)
        if not expense or expense.status == Expense.STATUS_DELETED:
            raise ExpenseServiceError("NOT_FOUND", "Expense not found.")

        self._require_active_member(expense.group_id, requester_user_id, error_code="NOT_GROUP_MEMBER")
        return expense

    def update_expense(self, expense_id: object, requester: Any, payload: dict[str, Any]) -> Expense:
        requester_user_id = self._request_user_id(requester)
        expense = ExpenseRepository.get_by_id(expense_id)
        if not expense or expense.status == Expense.STATUS_DELETED:
            raise ExpenseServiceError("NOT_FOUND", "Expense not found.")

        self._require_update_permission(expense, requester_user_id)

        merged = self._merged_update_payload(expense, payload)
        title = self._validated_title(merged.get("title"))
        currency = self._validated_currency(merged.get("currency", expense.currency))
        payer_member = self._require_active_member(
            expense.group_id,
            merged.get("payer_user_id"),
            error_code="PAYER_NOT_GROUP_MEMBER",
        )
        base_amount_minor = self._positive_amount(merged.get("base_amount_minor"))
        split_method = merged.get("split_method")

        base_shares = self._calculate_base_shares(split_method, merged, base_amount_minor)
        member_snapshots = self._require_active_participants(expense.group_id, base_shares)

        tax_type = merged.get("tax_type", Expense.TAX_NONE)
        service_fee_type = merged.get("service_fee_type", Expense.SERVICE_NONE)
        tax_amount_minor = calculate_tax_amount_minor(
            tax_type,
            base_amount_minor,
            tax_percentage=merged.get("tax_percentage"),
            tax_amount_minor=merged.get("tax_amount_minor"),
        )
        service_fee_amount_minor = calculate_service_fee_amount_minor(
            service_fee_type,
            base_amount_minor,
            service_fee_percentage=merged.get("service_fee_percentage"),
            service_fee_amount_minor=merged.get("service_fee_amount_minor"),
        )
        total_amount_minor = base_amount_minor + tax_amount_minor + service_fee_amount_minor

        tax_shares = distribute_proportional(tax_amount_minor, base_shares)
        service_fee_shares = distribute_proportional(service_fee_amount_minor, base_shares)
        participants = self._build_participants(
            base_shares,
            tax_shares,
            service_fee_shares,
            member_snapshots,
        )
        self._verify_totals(participants, total_amount_minor)

        with transaction.atomic():
            ExpenseRepository.update_expense(
                expense,
                title=title,
                description=merged.get("description") or None,
                currency=currency,
                payer_user_id=payer_member.user_id,
                base_amount_minor=base_amount_minor,
                tax_type=tax_type,
                tax_percentage=merged.get("tax_percentage") if tax_type == Expense.TAX_PERCENTAGE else None,
                tax_amount_minor=tax_amount_minor,
                service_fee_type=service_fee_type,
                service_fee_percentage=(
                    merged.get("service_fee_percentage")
                    if service_fee_type == Expense.SERVICE_PERCENTAGE
                    else None
                ),
                service_fee_amount_minor=service_fee_amount_minor,
                total_amount_minor=total_amount_minor,
                split_method=split_method,
                expense_date=merged.get("expense_date") or expense.expense_date,
                status=Expense.STATUS_UPDATED,
                version=expense.version + 1,
            )
            ExpenseRepository.replace_participants(expense, participants)

        event = expense_updated_event(expense, participants)
        self._publish(event)
        return ExpenseRepository.get_by_id(expense.id) or expense

    def delete_expense(self, expense_id: object, requester: Any) -> Expense:
        requester_user_id = self._request_user_id(requester)
        expense = ExpenseRepository.get_by_id(expense_id)
        if not expense or expense.status == Expense.STATUS_DELETED:
            raise ExpenseServiceError("NOT_FOUND", "Expense not found.")

        self._require_update_permission(expense, requester_user_id)
        ExpenseRepository.soft_delete(expense)

        event = expense_deleted_event(expense, deleted_by_user_id=requester_user_id)
        self._publish(event)
        return expense

    def _request_user_id(self, requester: Any) -> str:
        user_id = getattr(requester, "sub", None) or getattr(requester, "id", None)
        if not user_id:
            raise ExpensePermissionError(
                "NOT_AUTHENTICATED",
                "Authentication credentials were not provided.",
            )
        return str(user_id)

    def _require_active_group(self, group_id: object) -> GroupProjection:
        group = ProjectionRepository.get_group(group_id)
        if not group:
            raise ExpenseServiceError("GROUP_NOT_FOUND", "Group not found.")
        if group.status != GroupProjection.STATUS_ACTIVE:
            raise ExpenseServiceError("GROUP_NOT_ACTIVE", "Group must be active.")
        return group

    def _require_active_member(
        self,
        group_id: object,
        user_id: object,
        error_code: str,
    ) -> GroupMemberProjection:
        if not user_id:
            raise ExpenseServiceError(error_code, "User must be an active group member.")

        member = ProjectionRepository.get_active_member(group_id, user_id)
        if not member:
            if error_code == "NOT_GROUP_MEMBER":
                raise ExpensePermissionError(
                    "NOT_GROUP_MEMBER",
                    "You are not an active member of this group.",
                )
            raise ExpenseServiceError(error_code, "User must be an active group member.")
        return member

    def _require_active_participants(
        self,
        group_id: object,
        base_shares: dict[str, int],
    ) -> dict[str, GroupMemberProjection]:
        snapshots: dict[str, GroupMemberProjection] = {}
        for user_id in base_shares:
            member = ProjectionRepository.get_active_member(group_id, user_id)
            if not member:
                raise ExpenseServiceError(
                    "PARTICIPANT_NOT_GROUP_MEMBER",
                    "All participants must be active group members.",
                )
            snapshots[str(user_id)] = member
        return snapshots

    def _require_update_permission(self, expense: Expense, requester_user_id: str) -> None:
        if str(expense.created_by_user_id) == str(requester_user_id):
            return

        member = ProjectionRepository.get_active_member(expense.group_id, requester_user_id)
        if not member or member.role not in (
            GroupMemberProjection.ROLE_OWNER,
            GroupMemberProjection.ROLE_ADMIN,
        ):
            raise ExpensePermissionError("NOT_ALLOWED", "You are not allowed to modify this expense.")

    def _validated_title(self, title: object) -> str:
        normalized = str(title or "").strip()
        if not normalized:
            raise ExpenseServiceError("TITLE_REQUIRED", "Title is required.")
        return normalized

    def _validated_currency(self, currency: object) -> str:
        if str(currency or "IRR").upper() != "IRR":
            raise ExpenseServiceError("UNSUPPORTED_CURRENCY", "Only IRR is supported.")
        return "IRR"

    def _positive_amount(self, amount: object) -> int:
        try:
            amount_minor = int(amount)
        except (TypeError, ValueError) as exc:
            raise ExpenseServiceError("INVALID_AMOUNT", "base_amount_minor must be an integer.") from exc

        if amount_minor <= 0:
            raise ExpenseServiceError("INVALID_AMOUNT", "base_amount_minor must be greater than zero.")
        return amount_minor

    def _calculate_base_shares(
        self,
        split_method: object,
        payload: dict[str, Any],
        base_amount_minor: int,
    ) -> dict[str, int]:
        try:
            if split_method == Expense.SPLIT_EQUAL:
                return equal_split(payload.get("participant_user_ids"), base_amount_minor)
            if split_method == Expense.SPLIT_CUSTOM:
                return custom_split(payload.get("participants"), base_amount_minor)
        except ValueError as exc:
            code = str(exc)
            if code == INVALID_SPLIT_AMOUNT:
                raise ExpenseServiceError(
                    "INVALID_SPLIT_AMOUNT",
                    "Sum of participant shares must equal the base amount.",
                ) from exc
            raise ExpenseServiceError(code, code) from exc

        raise ExpenseServiceError("INVALID_SPLIT_METHOD", "split_method must be EQUAL or CUSTOM_AMOUNT.")

    def _build_participants(
        self,
        base_shares: dict[str, int],
        tax_shares: dict[str, int],
        service_fee_shares: dict[str, int],
        member_snapshots: dict[str, GroupMemberProjection],
    ) -> list[dict[str, Any]]:
        participants = []
        for user_id, base_share in base_shares.items():
            member = member_snapshots[user_id]
            tax_share = tax_shares.get(user_id, 0)
            service_fee_share = service_fee_shares.get(user_id, 0)
            participants.append(
                {
                    "user_id": UUID(str(user_id)),
                    "email": member.email or "",
                    "art_name_snapshot": member.art_name_snapshot,
                    "base_share_minor": int(base_share),
                    "tax_share_minor": int(tax_share),
                    "service_fee_share_minor": int(service_fee_share),
                    "total_share_minor": int(base_share) + int(tax_share) + int(service_fee_share),
                    "is_included": True,
                }
            )
        return participants

    def _verify_totals(self, participants: list[dict[str, Any]], total_amount_minor: int) -> None:
        if sum(int(row["total_share_minor"]) for row in participants) != int(total_amount_minor):
            raise ExpenseServiceError(
                "INVALID_PARTICIPANT_TOTAL",
                "Sum of participant totals must equal expense total amount.",
            )

    def _merged_update_payload(self, expense: Expense, payload: dict[str, Any]) -> dict[str, Any]:
        participants = list(expense.participants.all())

        if expense.split_method == Expense.SPLIT_EQUAL:
            participant_user_ids = [str(participant.user_id) for participant in participants]
            custom_participants: list[dict[str, Any]] = []
        else:
            participant_user_ids = []
            custom_participants = [
                {
                    "user_id": str(participant.user_id),
                    "base_share_minor": int(participant.base_share_minor),
                }
                for participant in participants
            ]

        return {
            "title": payload.get("title", expense.title),
            "description": payload.get("description", expense.description),
            "payer_user_id": payload.get("payer_user_id", expense.payer_user_id),
            "base_amount_minor": payload.get("base_amount_minor", expense.base_amount_minor),
            "currency": payload.get("currency", expense.currency),
            "split_method": payload.get("split_method", expense.split_method),
            "participant_user_ids": payload.get("participant_user_ids", participant_user_ids),
            "participants": payload.get("participants", custom_participants),
            "tax_type": payload.get("tax_type", expense.tax_type),
            "tax_percentage": payload.get("tax_percentage", expense.tax_percentage),
            "tax_amount_minor": payload.get("tax_amount_minor", expense.tax_amount_minor),
            "service_fee_type": payload.get("service_fee_type", expense.service_fee_type),
            "service_fee_percentage": payload.get(
                "service_fee_percentage",
                expense.service_fee_percentage,
            ),
            "service_fee_amount_minor": payload.get(
                "service_fee_amount_minor",
                expense.service_fee_amount_minor,
            ),
            "expense_date": payload.get("expense_date", expense.expense_date),
        }

    def _publish(self, event: dict[str, Any]) -> None:
        if hasattr(self.publisher, "publish_event"):
            self.publisher.publish_event(event)
            return

        self.publisher.publish(event["event_type"], event["data"], event["routing_key"])
