"""HTTP clients for settlement-service dependencies."""

from __future__ import annotations

from typing import Any

import httpx
from django.conf import settings


class IdentityBankCardClient:
    def __init__(self, base_url: str | None = None, service_token: str | None = None):
        self.base_url = (base_url or getattr(settings, "IDENTITY_SERVICE_URL", "")).rstrip("/")
        self.service_token = service_token or getattr(settings, "INTERNAL_SERVICE_TOKEN", "hamdong-internal-token")

    def resolve_payment_context_cards(self, owner_user_id: object, card_ids: list[object] | None = None) -> list[dict[str, Any]]:
        url = f"{self.base_url}/api/v1/internal/bank-cards/payment-context/"
        payload: dict[str, Any] = {"owner_user_id": str(owner_user_id)}
        if card_ids is not None:
            payload["card_ids"] = [str(card_id) for card_id in card_ids]
        response = httpx.post(
            url,
            json=payload,
            headers={"X-Internal-Service-Token": self.service_token},
            timeout=5.0,
        )
        response.raise_for_status()
        return response.json().get("items", [])
