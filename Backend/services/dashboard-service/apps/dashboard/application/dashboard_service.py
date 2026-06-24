from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import httpx
from django.conf import settings
from django.utils import timezone

from apps.dashboard.infrastructure.repositories import (
    ActivityRepository,
    GroupProjectionRepository,
    UserProjectionRepository,
)


FINAL_SETTLEMENT_STATUSES = {"CONFIRMED", "CANCELLED", "COMPLETED", "EXPIRED"}
ACTION_PRIORITY_ORDER = {"URGENT": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}
ACTION_TYPE_CHOICES = (
    "PAY_DEBT",
    "CONFIRM_RECEIVED_PAYMENT",
    "REVIEW_REJECTED_PAYMENT",
    "RESPOND_TO_GROUP_INVITATION",
    "FOLLOW_UP_OVERDUE_PAYMENT",
    "VIEW_IMPORTANT_NOTIFICATION",
)
ACTION_PRIORITY_CHOICES = tuple(ACTION_PRIORITY_ORDER.keys())
ACTIVITY_TYPE_CHOICES = (
    "GROUP_CREATED",
    "GROUP_MEMBER_JOINED",
    "GROUP_INVITATION_CREATED",
    "EXPENSE_CREATED",
    "EXPENSE_UPDATED",
    "EXPENSE_DELETED",
    "RECEIPT_UPLOADED",
    "SETTLEMENT_REPORTED",
    "SETTLEMENT_CONFIRMED",
    "SETTLEMENT_REJECTED",
    "SETTLEMENT_PLAN_ACTIVATED",
    "WALLET_PAYMENT_COMPLETED",
)


@dataclass(frozen=True)
class InternalNotificationRecord:
    id: str
    title: str
    body: str
    priority: str
    created_at: str
    updated_at: str | None = None


class InternalAPIClient:
    def __init__(self, timeout: float | None = None):
        self.timeout = timeout or float(getattr(settings, "INTERNAL_HTTP_TIMEOUT_SECONDS", 5.0))
        self.settlement_service_url = getattr(settings, "SETTLEMENT_SERVICE_URL", "http://settlement-service:8000").rstrip("/")
        self.group_service_url = getattr(settings, "GROUP_SERVICE_URL", "http://group-service:8000").rstrip("/")
        self.notification_service_url = getattr(settings, "NOTIFICATION_SERVICE_URL", "http://notification-service:8000").rstrip("/")

    def _headers(self, token: str | None) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def _get(self, base_url: str, path: str, token: str | None, params: dict[str, Any] | None = None) -> dict[str, Any] | list[Any]:
        with httpx.Client(base_url=base_url, timeout=self.timeout, headers=self._headers(token)) as client:
            response = client.get(path, params=params)
            response.raise_for_status()
            return response.json()

    def list_all_settlements(self, token: str | None, *, action_required: bool | None = None) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        cursor = None
        while True:
            params: dict[str, Any] = {"page_size": 100}
            if action_required is not None:
                params["action_required"] = "true" if action_required else "false"
            if cursor:
                params["cursor"] = cursor
            payload = self._get(self.settlement_service_url, "/api/v1/settlements/me/", token, params=params)
            results.extend(payload.get("results", []))
            cursor = payload.get("next_cursor")
            if not cursor:
                break
        return results

    def list_my_groups(self, token: str | None) -> list[dict[str, Any]]:
        payload = self._get(self.group_service_url, "/api/v1/groups/mine/", token)
        return payload if isinstance(payload, list) else payload.get("results", [])

    def get_unread_counts(self, token: str | None) -> dict[str, int]:
        payload = self._get(self.notification_service_url, "/api/v1/notifications/unread-count/", token)
        return {
            "unread_count": int(payload.get("unread_count") or 0),
            "important_unread_count": int(payload.get("important_unread_count") or 0),
        }

    def list_important_notifications(self, token: str | None) -> list[dict[str, Any]]:
        rows: dict[str, dict[str, Any]] = {}
        for priority in ("URGENT", "HIGH"):
            cursor = None
            while True:
                params = {
                    "page_size": 100,
                    "is_read": "false",
                    "priority": priority,
                }
                if cursor:
                    params["cursor"] = cursor
                payload = self._get(
                    self.notification_service_url,
                    "/api/v1/notifications/",
                    token,
                    params=params,
                )
                for item in payload.get("results", []):
                    rows[str(item["id"])] = item
                cursor = payload.get("next_cursor")
                if not cursor:
                    break
        return list(rows.values())


class DashboardAggregationService:
    def __init__(self, api_client: InternalAPIClient | None = None):
        self.api_client = api_client or InternalAPIClient()

    def _safe(self, fn, default):
        try:
            return fn()
        except Exception:
            return default

    def _is_pending_settlement(self, settlement: dict[str, Any]) -> bool:
        return str(settlement.get("status") or "") not in FINAL_SETTLEMENT_STATUSES

    def _group_counts(self, token: str | None) -> int:
        groups = self._safe(lambda: self.api_client.list_my_groups(token), [])
        return sum(1 for group in groups if str(group.get("status")) == "ACTIVE")

    def _action_priority_for_settlement(self, settlement: dict[str, Any]) -> str:
        status = str(settlement.get("status") or "")
        if status == "REJECTED":
            return "HIGH"
        return "HIGH"

    def _build_settlement_action(self, settlement: dict[str, Any]) -> dict[str, Any] | None:
        source_type = str(settlement.get("source_type") or "")
        source_id = settlement.get("source_id")
        direction = str(settlement.get("direction") or "")
        status = str(settlement.get("status") or "")
        action_required = settlement.get("action_required")
        counterparty = settlement.get("counterparty") or {}
        group = settlement.get("group") or {}
        amount_minor = int(settlement.get("amount_minor") or 0)
        currency = str(settlement.get("currency") or "")
        created_at = settlement.get("updated_at") or settlement.get("created_at")
        allowed_actions: list[dict[str, str]] = []

        if action_required == "PAY" and direction == "PAY":
            action_type = "PAY_DEBT"
            title = "Pay pending settlement"
            description = f"Pay {counterparty.get('art_name') or 'group member'} in {group.get('title') or 'your group'}."
            if source_type == "SETTLEMENT_PLAN_ITEM":
                allowed_actions = [
                    {
                        "key": "REPORT_PAID",
                        "method": "POST",
                        "path": f"/api/v1/settlement-plan-items/{source_id}/report-paid/",
                    }
                ]
        elif action_required == "CONFIRM" and direction == "RECEIVE":
            action_type = "CONFIRM_RECEIVED_PAYMENT"
            title = "Confirm reported payment"
            description = f"Confirm payment from {counterparty.get('art_name') or 'group member'} in {group.get('title') or 'your group'}."
            if source_type == "SETTLEMENT_PLAN_ITEM":
                allowed_actions = [
                    {
                        "key": "CONFIRM",
                        "method": "POST",
                        "path": f"/api/v1/settlement-plan-items/{source_id}/confirm/",
                    },
                    {
                        "key": "REJECT",
                        "method": "POST",
                        "path": f"/api/v1/settlement-plan-items/{source_id}/reject/",
                    },
                ]
            elif source_type == "MANUAL_SETTLEMENT":
                allowed_actions = [
                    {
                        "key": "CONFIRM",
                        "method": "POST",
                        "path": f"/api/v1/settlements/{source_id}/confirm/",
                    },
                    {
                        "key": "REJECT",
                        "method": "POST",
                        "path": f"/api/v1/settlements/{source_id}/reject/",
                    },
                ]
        elif status == "REJECTED" and direction == "PAY":
            action_type = "REVIEW_REJECTED_PAYMENT"
            title = "Review rejected payment"
            description = f"Review rejected settlement for {group.get('title') or 'your group'}."
            if source_type == "SETTLEMENT_PLAN_ITEM":
                allowed_actions = [
                    {
                        "key": "REPORT_PAID",
                        "method": "POST",
                        "path": f"/api/v1/settlement-plan-items/{source_id}/report-paid/",
                    }
                ]
            else:
                allowed_actions = []
        else:
            return None

        stable_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"dashboard-action:settlement:{source_type}:{source_id}:{action_type}"))
        return {
            "id": stable_id,
            "type": action_type,
            "priority": self._action_priority_for_settlement(settlement),
            "title": title,
            "description": description,
            "group": group,
            "source": {
                "service": "settlement-service",
                "type": source_type,
                "id": source_id,
            },
            "amount_minor": amount_minor,
            "currency": currency,
            "created_at": created_at,
            "due_at": None,
            "allowed_actions": allowed_actions,
        }

    def _build_notification_action(self, notification: dict[str, Any]) -> dict[str, Any]:
        notification_id = str(notification.get("id"))
        priority = str(notification.get("priority") or "HIGH")
        stable_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"dashboard-action:notification:{notification_id}:VIEW_IMPORTANT_NOTIFICATION"))
        return {
            "id": stable_id,
            "type": "VIEW_IMPORTANT_NOTIFICATION",
            "priority": priority if priority in ACTION_PRIORITY_ORDER else "HIGH",
            "title": str(notification.get("title") or "Important notification"),
            "description": str(notification.get("body") or ""),
            "group": None,
            "source": {
                "service": "notification-service",
                "type": "NOTIFICATION",
                "id": notification_id,
            },
            "amount_minor": None,
            "currency": None,
            "created_at": notification.get("created_at"),
            "due_at": None,
            "allowed_actions": [
                {
                    "key": "VIEW",
                    "method": "GET",
                    "path": f"/api/v1/notifications/{notification_id}/",
                },
                {
                    "key": "MARK_READ",
                    "method": "POST",
                    "path": f"/api/v1/notifications/{notification_id}/read/",
                },
            ],
        }

    def _encode_action_cursor(self, item: dict[str, Any]) -> str:
        return f"{item['priority']}|{item['created_at']}|{item['id']}"

    def _decode_action_cursor(self, value: str):
        try:
            priority, created_at, item_id = str(value).split("|", 2)
            return {
                "priority": priority,
                "created_at": created_at,
                "id": item_id,
            }
        except Exception as exc:
            raise ValueError("INVALID_CURSOR") from exc

    def _sort_actions(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return sorted(
            items,
            key=lambda item: (
                ACTION_PRIORITY_ORDER.get(str(item.get("priority")), 0),
                str(item.get("created_at") or ""),
                str(item.get("id")),
            ),
            reverse=True,
        )

    def list_action_items(self, token: str | None, filters: dict[str, Any] | None = None) -> tuple[list[dict[str, Any]], str | None]:
        filters = filters or {}
        settlements = self._safe(lambda: self.api_client.list_all_settlements(token), [])
        notifications = self._safe(lambda: self.api_client.list_important_notifications(token), [])

        items = []
        for settlement in settlements:
            action = self._build_settlement_action(settlement)
            if action:
                items.append(action)
        for notification in notifications:
            items.append(self._build_notification_action(notification))

        if filters.get("type"):
            items = [item for item in items if item["type"] == filters["type"]]
        if filters.get("priority"):
            items = [item for item in items if item["priority"] == filters["priority"]]
        if filters.get("group_id"):
            group_id = str(filters["group_id"])
            items = [
                item
                for item in items
                if item.get("group") and str(item["group"].get("id")) == group_id
            ]

        items = self._sort_actions(items)

        if filters.get("cursor"):
            cursor = self._decode_action_cursor(filters["cursor"])
            items = [
                item
                for item in items
                if (
                    ACTION_PRIORITY_ORDER.get(str(item.get("priority")), 0),
                    str(item.get("created_at") or ""),
                    str(item.get("id")),
                )
                < (
                    ACTION_PRIORITY_ORDER.get(cursor["priority"], 0),
                    cursor["created_at"],
                    cursor["id"],
                )
            ]

        page_size = min(int(filters.get("page_size") or 20), 100)
        rows = items[: page_size + 1]
        next_cursor = None
        if len(rows) > page_size:
            next_cursor = self._encode_action_cursor(rows[page_size - 1])
            rows = rows[:page_size]
        return rows, next_cursor

    def get_summary(self, token: str | None, *, currency: str | None = None) -> dict[str, Any]:
        settlements = self._safe(lambda: self.api_client.list_all_settlements(token), [])
        financial_totals: dict[str, dict[str, int]] = defaultdict(
            lambda: {
                "total_receivable_minor": 0,
                "total_payable_minor": 0,
                "net_balance_minor": 0,
            }
        )
        pending_settlements_count = 0

        for settlement in settlements:
            if not self._is_pending_settlement(settlement):
                continue
            pending_settlements_count += 1
            settlement_currency = str(settlement.get("currency") or "")
            amount_minor = int(settlement.get("amount_minor") or 0)
            direction = str(settlement.get("direction") or "")
            if direction == "RECEIVE":
                financial_totals[settlement_currency]["total_receivable_minor"] += amount_minor
                financial_totals[settlement_currency]["net_balance_minor"] += amount_minor
            elif direction == "PAY":
                financial_totals[settlement_currency]["total_payable_minor"] += amount_minor
                financial_totals[settlement_currency]["net_balance_minor"] -= amount_minor

        financials = []
        for item_currency, totals in sorted(financial_totals.items()):
            if currency and item_currency != currency:
                continue
            financials.append({"currency": item_currency, **totals})
        if currency and not financials:
            financials = [
                {
                    "currency": currency,
                    "total_receivable_minor": 0,
                    "total_payable_minor": 0,
                    "net_balance_minor": 0,
                }
            ]

        action_items, _ = self.list_action_items(token, {"page_size": 100})
        unread_counts = self._safe(lambda: self.api_client.get_unread_counts(token), {"unread_count": 0, "important_unread_count": 0})

        return {
            "financials": financials,
            "active_groups_count": self._group_counts(token),
            "pending_settlements_count": pending_settlements_count,
            "action_items_count": len(action_items),
            "important_unread_notifications_count": int(unread_counts.get("important_unread_count") or 0),
            "generated_at": timezone.now(),
        }


class DashboardActivityService:
    def list_feed(self, requester_user_id, filters: dict[str, Any] | None = None) -> tuple[list[dict[str, Any]], str | None]:
        filters = filters or {}
        rows, next_cursor = ActivityRepository.list_for_user(
            requester_user_id,
            group_id=filters.get("group_id"),
            event_type=filters.get("type"),
            from_date=filters.get("from"),
            to_date=filters.get("to"),
            cursor=filters.get("cursor"),
            page_size=filters.get("page_size") or 20,
        )
        items = []
        for row in rows:
            group = GroupProjectionRepository.get(row.group_id)
            actor = UserProjectionRepository.get(row.actor_user_id) if row.actor_user_id else None
            items.append(
                {
                    "id": row.id,
                    "type": row.event_type,
                    "group": {
                        "id": row.group_id,
                        "title": group.title if group else "",
                    },
                    "actor": {
                        "user_id": row.actor_user_id,
                        "art_name": actor.art_name if actor else None,
                    }
                    if row.actor_user_id
                    else None,
                    "occurred_at": row.occurred_at,
                    "summary": row.summary or {},
                }
            )
        return items, next_cursor
