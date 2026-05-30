from datetime import datetime
import uuid


def envelope(event_type: str, data: dict, version: str = "1.0") -> dict:
    return {
        "event_id": str(uuid.uuid4()),
        "event_type": event_type,
        "occurred_at": datetime.utcnow().isoformat() + "Z",
        "version": version,
        "data": data,
    }
"""Domain events for expense-service."""
