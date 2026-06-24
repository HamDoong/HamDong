from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID


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
