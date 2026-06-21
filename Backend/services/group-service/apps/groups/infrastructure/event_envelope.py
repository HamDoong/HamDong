from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from django.conf import settings


def _coerce_uuid(value: Any) -> str:
    if value in (None, ""):
        return str(uuid.uuid4())
    if isinstance(value, UUID):
        return str(value)
    return str(value)


def build_event_envelope(
    event_type: str,
    data: dict[str, Any],
    *,
    event_version: int = 1,
    source_service: str | None = None,
    routing_key: str,
    correlation_id: str | None = None,
    causation_id: str | None = None,
    event_id: str | None = None,
    occurred_at: str | None = None,
) -> dict[str, Any]:
    correlation_value = _coerce_uuid(correlation_id)
    causation_value = _coerce_uuid(causation_id or correlation_value)
    return {
        "event_id": _coerce_uuid(event_id),
        "event_type": event_type,
        "event_version": int(event_version),
        "occurred_at": occurred_at or datetime.now(timezone.utc).isoformat(),
        "source_service": source_service or getattr(settings, "SERVICE_NAME", "group-service"),
        "correlation_id": correlation_value,
        "causation_id": causation_value,
        "routing_key": routing_key,
        "data": data or {},
    }


def validate_event_envelope(payload: dict[str, Any]) -> tuple[bool, str | None]:
    required = (
        "event_id",
        "event_type",
        "event_version",
        "occurred_at",
        "source_service",
        "correlation_id",
        "causation_id",
        "routing_key",
        "data",
    )
    if not isinstance(payload, dict):
        return False, "Payload must be an object."
    for key in required:
        if key not in payload:
            return False, f"Missing required field: {key}"
    try:
        UUID(str(payload["event_id"]))
        UUID(str(payload["correlation_id"]))
        UUID(str(payload["causation_id"]))
    except Exception:
        return False, "Event envelope UUID fields are invalid."
    try:
        if int(payload["event_version"]) < 1:
            return False, "event_version must be >= 1."
    except Exception:
        return False, "event_version must be an integer."
    try:
        datetime.fromisoformat(str(payload["occurred_at"]).replace("Z", "+00:00"))
    except Exception:
        return False, "occurred_at must be a valid ISO datetime."
    if not isinstance(payload["data"], dict):
        return False, "data must be an object."
    return True, None
