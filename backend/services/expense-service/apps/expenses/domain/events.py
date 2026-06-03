"""Settlement-compatible expense domain event payloads."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


ROUTING_KEYS = {
    "ExpenseCreated": "expense.created",
    "ExpenseUpdated": "expense.updated",
    "ExpenseDeleted": "expense.deleted",
}


def event_envelope(event_type: str, data: dict[str, Any]) -> dict[str, Any]:
    """Build the standard event envelope used by expense-service."""
    return {
        "event_id": str(uuid4()),
        "event_type": event_type,
        "event_version": 1,
        "occurred_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "source_service": "expense-service",
        "routing_key": ROUTING_KEYS[event_type],
        "data": data,
    }


def _participant_payload(participant: Any) -> dict[str, Any]:
    if isinstance(participant, dict):
        return {
            "user_id": str(participant["user_id"]),
            "base_share_minor": int(participant["base_share_minor"]),
            "tax_share_minor": int(participant["tax_share_minor"]),
            "service_fee_share_minor": int(participant["service_fee_share_minor"]),
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
    """Build the common expense event data payload."""
    participant_rows = participants
    if participant_rows is None:
        participant_rows = list(expense.participants.all())

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
    """Build an ExpenseCreated event."""
    return event_envelope("ExpenseCreated", expense_payload(expense, participants))


def expense_updated_event(expense: Any, participants: list[Any] | None = None) -> dict[str, Any]:
    """Build an ExpenseUpdated event."""
    data = expense_payload(expense, participants)
    data["version"] = int(expense.version)
    data["status"] = expense.status
    return event_envelope("ExpenseUpdated", data)


def expense_deleted_event(expense: Any, deleted_by_user_id: object | None = None) -> dict[str, Any]:
    """Build an ExpenseDeleted event."""
    data = {
        "expense_id": str(expense.id),
        "group_id": str(expense.group_id),
        "deleted_by_user_id": str(deleted_by_user_id) if deleted_by_user_id else None,
        "status": expense.status,
    }
    return event_envelope("ExpenseDeleted", data)
