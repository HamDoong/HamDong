"""Event envelope helpers for group-service."""

import uuid
from datetime import datetime, timezone

from django.conf import settings

EVENT_VERSION = 1


def make_event(event_type: str, data: dict, routing_key: str | None = None) -> dict:
    envelope = {
        "event_id": str(uuid.uuid4()),
        "event_type": event_type,
        "event_version": EVENT_VERSION,
        "version": EVENT_VERSION,
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "source_service": getattr(settings, "SERVICE_NAME", "group-service"),
        "routing_key": routing_key,
        "correlation_id": None,
        "causation_id": None,
        "data": data,
    }
    return envelope
