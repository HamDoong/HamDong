"""Settlement-compatible expense domain event payloads."""

from __future__ import annotations

from typing import Any

from apps.expenses.infrastructure.event_envelope import build_event_envelope

ROUTING_KEYS = {
    "ExpenseCreated": "expense.created",
    "ExpenseUpdated": "expense.updated",
    "ExpenseDeleted": "expense.deleted",
    "ExpenseParticipantsChanged": "expense.participants.changed",
}


def event_envelope(event_type: str, data: dict[str, Any]) -> dict[str, Any]:
    return build_event_envelope(
        event_type,
        data,
        source_service="expense-service",
        routing_key=ROUTING_KEYS[event_type],
    )


def _participant_payload(participant: Any) -> dict[str, Any]:
    if isinstance(participant, dict):
        return {
            "user_id": str(participant["user_id"]),
            "base_share_minor": int(participant["base_share_minor"]),
            "tax_share_minor": int(participant.get("tax_share_minor", 0)),
            "service_fee_share_minor": int(participant.get("service_fee_share_minor", 0)),
            "total_share_minor": int(participant["total_share_minor"]),
        }
    return {
        "user_id": str(participant.user_id),
        "base_share_minor": int(participant.base_share_minor),
        "tax_share_minor": int(participant.tax_share_minor),
        "service_fee_share_minor": int(participant.service_fee_share_minor),
        "total_share_minor": int(participant.total_share_minor),
    }


def expense_payload(expense: Any, participants: list[Any] | None = None) -> dict[str, Any]:
    participant_rows = list(expense.participants.all()) if participants is None else participants
    return {
        "expense_id": str(expense.id),
        "group_id": str(expense.group_id),
        "created_by_user_id": str(expense.created_by_user_id),
        "payer_user_id": str(expense.payer_user_id),
        "currency": expense.currency,
        "base_amount_minor": int(expense.base_amount_minor),
        "tax_amount_minor": int(expense.tax_amount_minor),
        "service_fee_amount_minor": int(expense.service_fee_amount_minor),
        "total_amount_minor": int(expense.total_amount_minor),
        "participants": [_participant_payload(participant) for participant in participant_rows],
    }


def expense_created_event(expense: Any, participants: list[Any] | None = None) -> dict[str, Any]:
    return event_envelope("ExpenseCreated", expense_payload(expense, participants))


def expense_updated_event(expense: Any, participants: list[Any] | None = None) -> dict[str, Any]:
    data = expense_payload(expense, participants)
    data["version"] = int(expense.version)
    data["status"] = expense.status
    return event_envelope("ExpenseUpdated", data)


def expense_deleted_event(expense: Any, deleted_by_user_id: object | None = None) -> dict[str, Any]:
    return event_envelope("ExpenseDeleted", {
        "expense_id": str(expense.id),
        "group_id": str(expense.group_id),
        "deleted_by_user_id": str(deleted_by_user_id) if deleted_by_user_id else None,
        "status": expense.status,
    })
