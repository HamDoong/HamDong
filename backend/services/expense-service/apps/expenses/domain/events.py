from typing import Any
from uuid import uuid4

from django.utils import timezone

ROUTING_KEYS = {
    "ExpenseCreated": "expense.created",
    "ExpenseUpdated": "expense.updated",
    "ExpenseDeleted": "expense.deleted",
}


def _occurred_at() -> str:
    return timezone.now().replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _participant_payload(participant: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "user_id": str(participant["user_id"]),
        "base_share_minor": int(participant["base_share_minor"]),
        "tax_share_minor": int(participant["tax_share_minor"]),
        "service_fee_share_minor": int(participant["service_fee_share_minor"]),
        "total_share_minor": int(participant["total_share_minor"]),
    }
    if "phone_number" in participant:
        payload["phone_number"] = participant["phone_number"]
    if "display_name_snapshot" in participant:
        payload["display_name_snapshot"] = participant["display_name_snapshot"]
    if "is_included" in participant:
        payload["is_included"] = bool(participant["is_included"])
    return payload


def _build_event(event_type: str, data: dict[str, Any]) -> dict[str, Any]:
    return {
        "event_id": str(uuid4()),
        "event_type": event_type,
        "event_version": 1,
        "occurred_at": _occurred_at(),
        "source_service": "expense-service",
        "routing_key": ROUTING_KEYS[event_type],
        "data": data,
    }


def expense_created_event(
    *,
    expense_id: str,
    group_id: str,
    created_by_user_id: str,
    payer_user_id: str,
    currency: str,
    base_amount_minor: int,
    tax_amount_minor: int,
    service_fee_amount_minor: int,
    total_amount_minor: int,
    participants: list[dict[str, Any]],
) -> dict[str, Any]:
    return _build_event(
        "ExpenseCreated",
        {
            "expense_id": str(expense_id),
            "group_id": str(group_id),
            "created_by_user_id": str(created_by_user_id),
            "payer_user_id": str(payer_user_id),
            "currency": currency,
            "base_amount_minor": int(base_amount_minor),
            "tax_amount_minor": int(tax_amount_minor),
            "service_fee_amount_minor": int(service_fee_amount_minor),
            "total_amount_minor": int(total_amount_minor),
            "participants": [_participant_payload(participant) for participant in participants],
        },
    )


def expense_updated_event(
    *,
    expense_id: str,
    group_id: str,
    created_by_user_id: str,
    payer_user_id: str,
    currency: str,
    base_amount_minor: int,
    tax_amount_minor: int,
    service_fee_amount_minor: int,
    total_amount_minor: int,
    participants: list[dict[str, Any]],
) -> dict[str, Any]:
    return _build_event(
        "ExpenseUpdated",
        {
            "expense_id": str(expense_id),
            "group_id": str(group_id),
            "created_by_user_id": str(created_by_user_id),
            "payer_user_id": str(payer_user_id),
            "currency": currency,
            "base_amount_minor": int(base_amount_minor),
            "tax_amount_minor": int(tax_amount_minor),
            "service_fee_amount_minor": int(service_fee_amount_minor),
            "total_amount_minor": int(total_amount_minor),
            "participants": [_participant_payload(participant) for participant in participants],
        },
    )


def expense_deleted_event(
    *,
    expense_id: str,
    group_id: str,
) -> dict[str, Any]:
    return _build_event(
        "ExpenseDeleted",
        {
            "expense_id": str(expense_id),
            "group_id": str(group_id),
        },
    )
