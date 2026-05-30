"""Event envelope and constants for group events."""

from datetime import datetime
from django.conf import settings

EVENT_VERSION = "1.0"


def make_event(event_type: str, data: dict) -> dict:
    return {
        "version": EVENT_VERSION,
        "event_type": event_type,
        "service": getattr(settings, "SERVICE_NAME", "group-service"),
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "data": data,
    }
"""Domain events for group-service."""
