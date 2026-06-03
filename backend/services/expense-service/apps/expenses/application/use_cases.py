from typing import Any
from uuid import UUID

from django.db import transaction
from django.utils import timezone

from apps.expenses.application.split_calculator import custom_split, equal_split
from apps.expenses.application.tax_calculator import (
    calculate_service_fee_amount,
    calculate_tax_amount,
    distribute_service_fee_amount,
    distribute_tax_amount,
)
from apps.expenses.domain.events import (
    expense_created_event,
    expense_deleted_event,
    expense_updated_event,
)
from apps.expenses.domain.models import Expense, GroupMemberProjection
from apps.expenses.infrastructure.rabbitmq_publisher import RabbitMQPublisher
from apps.expenses.infrastructure.repositories import ExpenseRepository, ProjectionRepository


class ExpenseService:
    def __init__(self, publisher: RabbitMQPublisher | None = None):
        self.publisher = publisher or RabbitMQPublisher()

    @staticmethod
    def _request_user_id(user: Any) -> str:
        user_id = getattr(user, "sub", None) or getattr(user, "id", None)
        if not user_id:
            raise PermissionError("NOT_AUTHENTICATED")
        return str(user_id)

    @staticmethod
    def _stringify_uuid_list(values: list[Any]) -> list[str]:
        return [str(value) for value in values]

    def _get_active_group(self, group_id):
        group = ProjectionRepository.get_group(group_id)
        if not group or group.status != "ACTIVE":
            raise ValueError("GROUP_NOT_ACTIVE")
        return group

    def _ensure_active_member(self, group_id, user_id, *, error_code: str = "NOT_GROUP_MEMBER"):
        if not ProjectionRepository.is_active_member(group_id, user_id):
            if error_code == "NOT_GROUP_MEMBER":
                raise PermissionError(error_code)
            raise ValueError(error_code)

    def _ensure_title(self, title: str | None):
        if not title or not str(title).strip():
            raise ValueError("TITLE_REQUIRED")

    def _ensure_currency(self, currency: str):
        if currency != "IRR":
            raise ValueError("INVALID_CURRENCY")

    def _get_existing_participant_payload(self, expense: Expense) -> dict[str, Any]:
        participant_records = list(expense.participants.order_by("created_at"))
        if expense.split_method == Expense.SPLIT_EQUAL:
            return {
                "participant_user_ids": [str(participant.user_id) for participant in participant_records]
            }
        return {
            "participants": [
                {
                    "user_id": str(participant.user_id),
                    "base_share_minor": int(participant.base_share_minor),
                }
                for participant in participant_records
            ]
        }

    def _build_base_shares(self, payload: dict[str, Any]) -> dict[str, int]:
        split_method = payload.get("split_method")
        base_amount_minor = int(payload["base_amount_minor"])

        if split_method == Expense.SPLIT_EQUAL:
            participant_user_ids = self._stringify_uuid_list(payload.get("participant_user_ids", []))
            return equal_split(participant_user_ids, base_amount_minor)

        if split_method == Expense.SPLIT_CUSTOM:
            participants = payload.get("participants", [])
            return custom_split(participants, base_amount_minor)

        raise ValueError("INVALID_SPLIT_METHOD")

    def _get_active_participant_members(
        self,
        *,
        group_id,
        payer_user_id: str,
        participant_user_ids: list[str],
    ) -> dict[str, GroupMemberProjection]:
        unique_user_ids = list(dict.fromkeys([payer_user_id, *participant_user_ids]))
        active_members = ProjectionRepository.get_active_members_map(group_id, unique_user_ids)
        if payer_user_id not in active_members:
            raise ValueError("INVALID_PAYER")

        missing_participants = [user_id for user_id in participant_user_ids if user_id not in active_members]
        if missing_participants:
            raise ValueError("INVALID_PARTICIPANT")

        return active_members

    def _calculate_additional_amounts(self, payload: dict[str, Any]) -> tuple[int, int]:
        base_amount_minor = int(payload["base_amount_minor"])
        tax_amount_minor = calculate_tax_amount(
            tax_type=payload.get("tax_type", Expense.TAX_NONE),
            base_amount_minor=base_amount_minor,
            tax_percentage=payload.get("tax_percentage"),
            tax_amount_minor=payload.get("tax_amount_minor"),
        )
        service_fee_amount_minor = calculate_service_fee_amount(
            service_fee_type=payload.get("service_fee_type", Expense.SERVICE_NONE),
            base_amount_minor=base_amount_minor,
            service_fee_percentage=payload.get("service_fee_percentage"),
            service_fee_amount_minor=payload.get("service_fee_amount_minor"),
        )
        return tax_amount_minor, service_fee_amount_minor

    def _build_participant_rows(
        self,
        *,
        active_members: dict[str, GroupMemberProjection],
        base_shares: dict[str, int],
        tax_shares: dict[str, int],
        service_fee_shares: dict[str, int],
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for user_id, base_share_minor in base_shares.items():
            member = active_members[user_id]
            tax_share_minor = int(tax_shares.get(user_id, 0))
            service_fee_share_minor = int(service_fee_shares.get(user_id, 0))
            rows.append(
                {
                    "user_id": user_id,
                    "phone_number": member.phone_number,
                    "display_name_snapshot": member.display_name_snapshot,
                    "base_share_minor": int(base_share_minor),
                    "tax_share_minor": tax_share_minor,
                    "service_fee_share_minor": service_fee_share_minor,
                    "total_share_minor": int(base_share_minor) + tax_share_minor + service_fee_share_minor,
                    "is_included": True,
                }
            )
        return rows

    def _prepare_expense_payload(
        self,
        *,
        group_id,
        creator,
        payload: dict[str, Any],
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        creator_user_id = self._request_user_id(creator)
        self._get_active_group(group_id)
        self._ensure_active_member(group_id, creator_user_id, error_code="NOT_GROUP_MEMBER")

        self._ensure_title(payload.get("title"))
        self._ensure_currency(payload.get("currency", "IRR"))

        base_amount_minor = int(payload.get("base_amount_minor", 0))
        if base_amount_minor <= 0:
            raise ValueError("INVALID_AMOUNT")

        payer_user_id = str(payload["payer_user_id"])
        base_shares = self._build_base_shares(payload)
        active_members = self._get_active_participant_members(
            group_id=group_id,
            payer_user_id=payer_user_id,
            participant_user_ids=list(base_shares.keys()),
        )

        tax_amount_minor, service_fee_amount_minor = self._calculate_additional_amounts(payload)
        tax_shares = distribute_tax_amount(
            tax_amount_minor=tax_amount_minor,
            base_shares=base_shares,
        )
        service_fee_shares = distribute_service_fee_amount(
            service_fee_amount_minor=service_fee_amount_minor,
            base_shares=base_shares,
        )

        participant_rows = self._build_participant_rows(
            active_members=active_members,
            base_shares=base_shares,
            tax_shares=tax_shares,
            service_fee_shares=service_fee_shares,
        )

        total_amount_minor = base_amount_minor + tax_amount_minor + service_fee_amount_minor
        participant_total = sum(participant["total_share_minor"] for participant in participant_rows)
        if participant_total != total_amount_minor:
            raise ValueError("PARTICIPANT_TOTAL_MISMATCH")

        expense_payload = {
            "group_id": group_id,
            "created_by_user_id": creator_user_id,
            "payer_user_id": payer_user_id,
            "title": payload["title"],
            "description": payload.get("description"),
            "currency": payload.get("currency", "IRR"),
            "base_amount_minor": base_amount_minor,
            "tax_type": payload.get("tax_type", Expense.TAX_NONE),
            "tax_percentage": payload.get("tax_percentage"),
            "tax_amount_minor": tax_amount_minor,
            "service_fee_type": payload.get("service_fee_type", Expense.SERVICE_NONE),
            "service_fee_percentage": payload.get("service_fee_percentage"),
            "service_fee_amount_minor": service_fee_amount_minor,
            "total_amount_minor": total_amount_minor,
            "split_method": payload["split_method"],
            "receipt_file_id": payload.get("receipt_file_id"),
            "receipt_url": payload.get("receipt_url"),
            "expense_date": payload.get("expense_date") or timezone.now(),
        }
        return expense_payload, participant_rows

    def _serialize_participants_for_event(self, participants: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "user_id": str(participant["user_id"]),
                "phone_number": participant["phone_number"],
                "display_name_snapshot": participant.get("display_name_snapshot"),
                "base_share_minor": int(participant["base_share_minor"]),
                "tax_share_minor": int(participant["tax_share_minor"]),
                "service_fee_share_minor": int(participant["service_fee_share_minor"]),
                "total_share_minor": int(participant["total_share_minor"]),
                "is_included": bool(participant.get("is_included", True)),
            }
            for participant in participants
        ]

    @transaction.atomic
    def create_expense(self, group_id, creator, payload: dict[str, Any]):
        expense_payload, participant_rows = self._prepare_expense_payload(
            group_id=group_id,
            creator=creator,
            payload=payload,
        )

        expense = ExpenseRepository.create_expense(**expense_payload)
        ExpenseRepository.add_participants(expense, participant_rows)

        event = expense_created_event(
            expense_id=str(expense.id),
            group_id=str(expense.group_id),
            created_by_user_id=str(expense.created_by_user_id),
            payer_user_id=str(expense.payer_user_id),
            currency=expense.currency,
            base_amount_minor=expense.base_amount_minor,
            tax_amount_minor=expense.tax_amount_minor,
            service_fee_amount_minor=expense.service_fee_amount_minor,
            total_amount_minor=expense.total_amount_minor,
            participants=self._serialize_participants_for_event(participant_rows),
        )
        self.publisher.publish(event)
        return ExpenseRepository.get_by_id(expense.id)

    def list_expenses(self, group_id, requester, filters: dict | None = None, page: int = 1, page_size: int = 50):
        requester_user_id = self._request_user_id(requester)
        self._get_active_group(group_id)
        self._ensure_active_member(group_id, requester_user_id, error_code="NOT_GROUP_MEMBER")
        return ExpenseRepository.list_by_group(group_id, filters=filters, page=page, page_size=page_size)

    def get_expense(self, expense_id, requester):
        requester_user_id = self._request_user_id(requester)
        expense = ExpenseRepository.get_by_id(expense_id)
        if not expense or expense.status == Expense.STATUS_DELETED:
            raise ValueError("NOT_FOUND")
        self._ensure_active_member(expense.group_id, requester_user_id, error_code="NOT_GROUP_MEMBER")
        return expense

    def _check_update_permission(self, expense: Expense, requester):
        requester_user_id = self._request_user_id(requester)
        if requester_user_id == str(expense.created_by_user_id):
            return

        member = ProjectionRepository.get_member(
            expense.group_id,
            requester_user_id,
            active_only=True,
        )
        if not member or member.role not in {
            GroupMemberProjection.ROLE_OWNER,
            GroupMemberProjection.ROLE_ADMIN,
        }:
            raise PermissionError("NOT_ALLOWED")

    @transaction.atomic
    def update_expense(self, expense_id, requester, payload: dict[str, Any]):
        expense = ExpenseRepository.get_by_id(expense_id)
        if not expense or expense.status == Expense.STATUS_DELETED:
            raise ValueError("NOT_FOUND")

        self._check_update_permission(expense, requester)
        self._get_active_group(expense.group_id)

        existing_payload = {
            "title": expense.title,
            "description": expense.description,
            "payer_user_id": str(expense.payer_user_id),
            "base_amount_minor": expense.base_amount_minor,
            "currency": expense.currency,
            "split_method": expense.split_method,
            "tax_type": expense.tax_type,
            "tax_percentage": expense.tax_percentage,
            "tax_amount_minor": expense.tax_amount_minor,
            "service_fee_type": expense.service_fee_type,
            "service_fee_percentage": expense.service_fee_percentage,
            "service_fee_amount_minor": expense.service_fee_amount_minor,
            "expense_date": expense.expense_date,
            **self._get_existing_participant_payload(expense),
        }
        merged_payload = {**existing_payload, **payload}

        prepared_expense_payload, participant_rows = self._prepare_expense_payload(
            group_id=expense.group_id,
            creator=requester if str(getattr(requester, "sub", getattr(requester, "id", ""))) == str(expense.created_by_user_id) else type("CreatorProxy", (), {"sub": expense.created_by_user_id})(),
            payload=merged_payload,
        )
        prepared_expense_payload["created_by_user_id"] = expense.created_by_user_id
        prepared_expense_payload["status"] = Expense.STATUS_UPDATED
        prepared_expense_payload["version"] = int(expense.version) + 1

        ExpenseRepository.update_expense(expense, **prepared_expense_payload)
        ExpenseRepository.replace_participants(expense, participant_rows)

        event = expense_updated_event(
            expense_id=str(expense.id),
            group_id=str(expense.group_id),
            created_by_user_id=str(expense.created_by_user_id),
            payer_user_id=str(expense.payer_user_id),
            currency=expense.currency,
            base_amount_minor=expense.base_amount_minor,
            tax_amount_minor=expense.tax_amount_minor,
            service_fee_amount_minor=expense.service_fee_amount_minor,
            total_amount_minor=expense.total_amount_minor,
            participants=self._serialize_participants_for_event(participant_rows),
        )
        self.publisher.publish(event)
        return ExpenseRepository.get_by_id(expense.id)

    @transaction.atomic
    def delete_expense(self, expense_id, requester):
        expense = ExpenseRepository.get_by_id(expense_id)
        if not expense or expense.status == Expense.STATUS_DELETED:
            raise ValueError("NOT_FOUND")

        self._check_update_permission(expense, requester)
        expense.deleted_at = timezone.now()
        expense.version = int(expense.version) + 1
        ExpenseRepository.soft_delete(expense)

        event = expense_deleted_event(
            expense_id=str(expense.id),
            group_id=str(expense.group_id),
        )
        self.publisher.publish(event)
        return expense
