import uuid
from datetime import datetime, timezone


def build_event_envelope(
    event_type: str,
    data: dict,
    *,
    version: int = 1,
    source_service: str = "settlement-service",
    routing_key: str | None = None,
    correlation_id: str | None = None,
    causation_id: str | None = None,
    event_id: str | None = None,
) -> dict:
    return {
        "event_id": event_id or str(uuid.uuid4()),
        "event_type": event_type,
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "version": version,
        "source_service": source_service,
        "routing_key": routing_key,
        "correlation_id": correlation_id,
        "causation_id": causation_id,
        "data": data,
    }
