from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterable
from uuid import uuid4

from django.conf import settings
from django.db import IntegrityError, connection, transaction
from django.db.models import Q
from django.utils import timezone

from apps.settlements.domain.models import (
    CurrencyChoices,
    DebtReminderSourceChoices,
    DebtReminderStatusChoices,
    GroupMemberRoleChoices,
    GroupMemberStatusChoices,
    GroupStatusChoices,
    ReminderChannelChoices,
    SettlementPlanItemStatusChoices,
    SettlementPlanStatusChoices,
)
from apps.settlements.domain.reminder_rules import (
    ReminderConflictError,
    ReminderEligibilityError,
    ReminderNotFoundError,
    ReminderPermissionDeniedError,
    ReminderRateLimitedError,
    ReminderSettingsValidationError,
    ensure_can_manage_settings,
    ensure_can_view_reminder_detail,
    ensure_can_view_settings,
    ensure_group_exists,
)
from apps.settlements.infrastructure.event_envelope import build_event_envelope
from apps.settlements.infrastructure.repositories import (
    DebtReminderRequestRepository,
    GroupMemberProjectionRepository,
    GroupProjectionRepository,
    GroupReminderSettingsRepository,
    OutboxRepository,
    SettlementPlanItemRepository,
    SettlementPlanRepository,
    UserProjectionRepository,
)


@dataclass
class EligibilityDecision:
    eligible: bool
    reason: str | None = None
    settings: object | None = None
    item: object | None = None
    plan: object | None = None
    source_timestamp: object | None = None
    channels: list[str] | None = None
    prior_count: int = 0
    sequence_number: int = 1


class ReminderService:
    def __init__(self) -> None:
        self.exchange = getattr(settings, "SETTLEMENT_REMINDER_EXCHANGE", "hamdong.settlement")
        self.scheduler_batch_size = int(getattr(settings, "REMINDER_SCHEDULER_BATCH_SIZE", 100))
        self.manual_cooldown_minutes = int(getattr(settings, "MANUAL_REMINDER_COOLDOWN_MINUTES", 30))
        self.default_first_after = int(getattr(settings, "DEFAULT_FIRST_REMINDER_AFTER_HOURS", 24))
        self.default_repeat_after = int(getattr(settings, "DEFAULT_REMINDER_REPEAT_INTERVAL_HOURS", 48))
        self.default_maximum = int(getattr(settings, "DEFAULT_MAXIMUM_REMINDERS", 3))
        self.minimum_interval = int(getattr(settings, "MINIMUM_REMINDER_INTERVAL_HOURS", 1))
        self.maximum_interval = int(getattr(settings, "MAXIMUM_REMINDER_INTERVAL_HOURS", 720))
        self.maximum_automatic_reminders = int(getattr(settings, "MAXIMUM_AUTOMATIC_REMINDERS", 10))

    def _settings_defaults(self, group_id, actor_user_id=None):
        return GroupReminderSettingsRepository.defaults(
            group_id=group_id,
            created_by_user_id=actor_user_id,
            updated_by_user_id=actor_user_id,
        ) | {
            "first_reminder_after_hours": self.default_first_after,
            "repeat_interval_hours": self.default_repeat_after,
            "maximum_reminders": self.default_maximum,
        }

    def _group_and_member(self, group_id, user_id):
        group = GroupProjectionRepository.get(group_id)
        ensure_group_exists(group)
        member = GroupMemberProjectionRepository.get(group_id, user_id)
        return group, member

    def _active_member(self, group_id, user_id):
        return GroupMemberProjectionRepository.get_active_member(group_id, user_id)

    def _settings_payload(self, settings_obj, *, group_id):
        return {
            "group_id": str(group_id),
            "is_enabled": settings_obj.is_enabled,
            "first_reminder_after_hours": settings_obj.first_reminder_after_hours,
            "repeat_interval_hours": settings_obj.repeat_interval_hours,
            "maximum_reminders": settings_obj.maximum_reminders,
            "send_in_app": settings_obj.send_in_app,
            "send_email": settings_obj.send_email,
            "created_at": settings_obj.created_at.isoformat() if settings_obj.created_at else None,
            "updated_at": settings_obj.updated_at.isoformat() if settings_obj.updated_at else None,
        }

    def _validate_settings_patch(self, payload: dict, *, existing):
        if not payload:
            raise ReminderSettingsValidationError("At least one field must be provided.")
        allowed_fields = {
            "is_enabled",
            "first_reminder_after_hours",
            "repeat_interval_hours",
            "maximum_reminders",
            "send_in_app",
            "send_email",
        }
        unknown = sorted(set(payload.keys()) - allowed_fields)
        if unknown:
            raise ReminderSettingsValidationError(f"Unknown fields: {', '.join(unknown)}")

        for field in ("is_enabled", "send_in_app", "send_email"):
            if field in payload and not isinstance(payload[field], bool):
                raise ReminderSettingsValidationError(f"{field} must be a boolean value.")

        for field in ("first_reminder_after_hours", "repeat_interval_hours", "maximum_reminders"):
            if field in payload:
                value = payload[field]
                if isinstance(value, bool) or not isinstance(value, int):
                    raise ReminderSettingsValidationError(f"{field} must be an integer.")

        if "first_reminder_after_hours" in payload and payload["first_reminder_after_hours"] <= 0:
            raise ReminderSettingsValidationError("first_reminder_after_hours must be greater than zero.")
        if "repeat_interval_hours" in payload and payload["repeat_interval_hours"] <= 0:
            raise ReminderSettingsValidationError("repeat_interval_hours must be greater than zero.")
        if "maximum_reminders" in payload and payload["maximum_reminders"] < 0:
            raise ReminderSettingsValidationError("maximum_reminders must be zero or greater.")

        first_after = payload.get("first_reminder_after_hours", existing.first_reminder_after_hours)
        repeat_after = payload.get("repeat_interval_hours", existing.repeat_interval_hours)
        maximum_reminders = payload.get("maximum_reminders", existing.maximum_reminders)
        is_enabled = payload.get("is_enabled", existing.is_enabled)
        send_in_app = payload.get("send_in_app", existing.send_in_app)
        send_email = payload.get("send_email", existing.send_email)

        if repeat_after < self.minimum_interval:
            raise ReminderSettingsValidationError(
                f"repeat_interval_hours must be at least {self.minimum_interval}."
            )
        if repeat_after > self.maximum_interval:
            raise ReminderSettingsValidationError(
                f"repeat_interval_hours must be at most {self.maximum_interval}."
            )
        if maximum_reminders > self.maximum_automatic_reminders:
            raise ReminderSettingsValidationError(
                f"maximum_reminders must be at most {self.maximum_automatic_reminders}."
            )
        if first_after > self.maximum_interval:
            raise ReminderSettingsValidationError(
                f"first_reminder_after_hours must be at most {self.maximum_interval}."
            )
        if is_enabled and not (send_in_app or send_email):
            raise ReminderSettingsValidationError(
                "At least one notification channel must be enabled while reminders are enabled."
            )
        return {
            "is_enabled": is_enabled,
            "first_reminder_after_hours": first_after,
            "repeat_interval_hours": repeat_after,
            "maximum_reminders": maximum_reminders,
            "send_in_app": send_in_app,
            "send_email": send_email,
        }

    def get_group_settings(self, group_id, user_id):
        group, member = self._group_and_member(group_id, user_id)
        ensure_can_view_settings(member)
        settings_obj = GroupReminderSettingsRepository.get_or_create(
            group.group_id,
            defaults=self._settings_defaults(group.group_id, actor_user_id=user_id),
        )
        return self._settings_payload(settings_obj, group_id=group.group_id)

    @transaction.atomic
    def update_group_settings(self, group_id, user_id, payload: dict):
        group, member = self._group_and_member(group_id, user_id)
        ensure_can_manage_settings(member)
        settings_obj = GroupReminderSettingsRepository.get_or_create(
            group.group_id,
            defaults=self._settings_defaults(group.group_id, actor_user_id=user_id),
        )
        settings_obj = GroupReminderSettingsRepository.lock_for_update(group.group_id) or settings_obj
        changes = self._validate_settings_patch(payload, existing=settings_obj)
        changes["updated_by_user_id"] = user_id
        GroupReminderSettingsRepository.save(settings_obj, **changes)
        return self._settings_payload(settings_obj, group_id=group.group_id)

    def list_group_history(self, group_id, user_id, filters: dict):
        group, member = self._group_and_member(group_id, user_id)
        ensure_can_manage_settings(member)
        qs = DebtReminderRequestRepository.list_for_group(group.group_id)
        if filters.get("status"):
            qs = qs.filter(status=filters["status"])
        if filters.get("recipient_user_id"):
            qs = qs.filter(recipient_user_id=filters["recipient_user_id"])
        if filters.get("settlement_plan_item_id"):
            qs = qs.filter(settlement_plan_item_id=filters["settlement_plan_item_id"])
        if filters.get("source"):
            qs = qs.filter(source=filters["source"])
        if filters.get("from"):
            qs = qs.filter(created_at__gte=filters["from"])
        if filters.get("to"):
            qs = qs.filter(created_at__lte=filters["to"])
        if filters.get("cursor"):
            created_at, reminder_id = self._decode_cursor(filters["cursor"])
            qs = qs.filter(Q(created_at__lt=created_at) | Q(created_at=created_at, id__lt=reminder_id))
        page_size = min(int(filters.get("page_size") or 20), 100)
        items = list(qs[: page_size + 1])
        next_cursor = None
        if len(items) > page_size:
            last = items[page_size - 1]
            next_cursor = self._encode_cursor(last.created_at, last.id)
            items = items[:page_size]
        return items, next_cursor

    def get_reminder_detail(self, reminder_id, user_id):
        reminder = DebtReminderRequestRepository.get(reminder_id)
        if not reminder:
            raise ReminderNotFoundError()
        member = GroupMemberProjectionRepository.get(reminder.group_id, user_id)
        ensure_can_view_reminder_detail(reminder, user_id, member)
        return reminder

    def _encode_cursor(self, created_at, reminder_id):
        return f"{created_at.isoformat()}|{reminder_id}"

    def _decode_cursor(self, value):
        created_at, reminder_id = str(value).split("|", 1)
        return datetime.fromisoformat(created_at), reminder_id

    def _build_channels(self, settings_obj, requested_channels=None):
        if requested_channels is None:
            channels = []
            if settings_obj.send_in_app:
                channels.append(ReminderChannelChoices.IN_APP)
            if settings_obj.send_email:
                channels.append(ReminderChannelChoices.EMAIL)
        else:
            channels = list(dict.fromkeys(requested_channels))
        if not channels:
            raise ReminderEligibilityError("At least one reminder delivery channel must be selected.")
        return channels

    def _lock_item_queryset(self):
        qs = SettlementPlanItemRepository._base_queryset()
        if connection.vendor == "postgresql":
            return qs.select_for_update(skip_locked=True)
        return qs.select_for_update()

    def _source_timestamp(self, plan, item):
        return plan.activated_at or plan.updated_at or item.created_at

    def _scheduled_prior_qs(self, item_id):
        return DebtReminderRequestRepository.list_for_item(item_id).exclude(
            source=DebtReminderSourceChoices.MANUAL_ITEM
        )

    def _automatic_prior_count(self, item_id):
        return self._scheduled_prior_qs(item_id).count()

    def evaluate_item(self, item_id, *, source, requested_by_user_id=None, channels_override=None):
        item = SettlementPlanItemRepository.get(item_id)
        if not item:
            return EligibilityDecision(False, "item_not_found")
        plan = SettlementPlanRepository.get(item.settlement_plan_id)
        if not plan:
            return EligibilityDecision(False, "plan_not_found")
        group = GroupProjectionRepository.get(plan.group_id)
        if not group or group.status != GroupStatusChoices.ACTIVE:
            return EligibilityDecision(False, "group_inactive")
        settings_obj = GroupReminderSettingsRepository.get_or_create(
            plan.group_id,
            defaults=self._settings_defaults(plan.group_id, actor_user_id=requested_by_user_id),
        )
        if not settings_obj.is_enabled and source != DebtReminderSourceChoices.MANUAL_ITEM:
            return EligibilityDecision(False, "settings_disabled", settings=settings_obj, item=item, plan=plan)
        try:
            channels = self._build_channels(settings_obj, channels_override)
        except ReminderEligibilityError:
            return EligibilityDecision(False, "channels_disabled", settings=settings_obj, item=item, plan=plan)
        if plan.status != SettlementPlanStatusChoices.ACTIVE:
            return EligibilityDecision(False, "plan_inactive", settings=settings_obj, item=item, plan=plan)
        if item.status != SettlementPlanItemStatusChoices.PENDING:
            return EligibilityDecision(False, "item_not_pending", settings=settings_obj, item=item, plan=plan)
        if int(item.amount_minor) <= 0:
            return EligibilityDecision(False, "amount_not_positive", settings=settings_obj, item=item, plan=plan)
        if item.currency != CurrencyChoices.IRR:
            return EligibilityDecision(False, "invalid_currency", settings=settings_obj, item=item, plan=plan)
        recipient_member = self._active_member(plan.group_id, item.payer_user_id)
        if not recipient_member:
            return EligibilityDecision(False, "recipient_inactive", settings=settings_obj, item=item, plan=plan)
        recipient_user = UserProjectionRepository.get(item.payer_user_id)
        if recipient_user and not recipient_user.is_active:
            return EligibilityDecision(False, "recipient_user_inactive", settings=settings_obj, item=item, plan=plan)

        source_timestamp = self._source_timestamp(plan, item)
        now = timezone.now()
        prior_scheduled_qs = self._scheduled_prior_qs(item.id)
        prior_scheduled = list(prior_scheduled_qs[: max(settings_obj.maximum_reminders, 1) + 5])

        if source in (DebtReminderSourceChoices.AUTOMATIC, DebtReminderSourceChoices.MANUAL_GROUP_RUN):
            if not settings_obj.is_enabled:
                return EligibilityDecision(False, "settings_disabled", settings=settings_obj, item=item, plan=plan)
            if now < source_timestamp + timedelta(hours=settings_obj.first_reminder_after_hours):
                return EligibilityDecision(False, "before_first_delay", settings=settings_obj, item=item, plan=plan, source_timestamp=source_timestamp)
            prior_count = len(prior_scheduled)
            if prior_count >= settings_obj.maximum_reminders:
                return EligibilityDecision(False, "maximum_reminders_reached", settings=settings_obj, item=item, plan=plan, source_timestamp=source_timestamp, channels=channels, prior_count=prior_count)
            latest = prior_scheduled[0] if prior_scheduled else None
            if latest and latest.requested_at and now < latest.requested_at + timedelta(hours=settings_obj.repeat_interval_hours):
                return EligibilityDecision(False, "before_repeat_interval", settings=settings_obj, item=item, plan=plan, source_timestamp=source_timestamp, channels=channels, prior_count=prior_count)
            sequence_number = prior_count + 1
        else:
            recent = DebtReminderRequestRepository.latest_manual_with_cooldown(
                item.id,
                requested_by_user_id,
                now - timedelta(minutes=self.manual_cooldown_minutes),
            )
            if recent:
                return EligibilityDecision(False, "manual_cooldown", settings=settings_obj, item=item, plan=plan, source_timestamp=source_timestamp, channels=channels)
            sequence_number = DebtReminderRequestRepository.list_for_item(item.id).count() + 1

        return EligibilityDecision(
            True,
            settings=settings_obj,
            item=item,
            plan=plan,
            source_timestamp=source_timestamp,
            channels=channels,
            prior_count=len(prior_scheduled),
            sequence_number=sequence_number,
        )

    def _event_payload(self, reminder, *, plan, item, group, recipient_user, creditor_user, channels, requested_by_user_id):
        send_in_app = ReminderChannelChoices.IN_APP in channels
        send_email = ReminderChannelChoices.EMAIL in channels
        return {
            "reminder_id": str(reminder.id),
            "source": reminder.source,
            "sequence_number": reminder.sequence_number,
            "group_id": str(group.group_id),
            "group_title": group.title,
            "settlement_plan_id": str(plan.id),
            "settlement_plan_item_id": str(item.id),
            "recipient_user_id": str(reminder.recipient_user_id),
            "recipient_email": recipient_user.email if recipient_user else None,
            "creditor_user_id": str(reminder.creditor_user_id),
            "creditor_name": creditor_user.art_name if creditor_user else None,
            "amount_minor": int(reminder.amount_minor),
            "currency": reminder.currency,
            "send_in_app": send_in_app,
            "send_email": send_email,
            "requested_by_user_id": str(requested_by_user_id) if requested_by_user_id else None,
        }

    def _create_reminder(self, decision: EligibilityDecision, *, source, requested_by_user_id=None, channels_override=None):
        item = decision.item
        plan = decision.plan
        group = GroupProjectionRepository.get(plan.group_id)
        recipient_user = UserProjectionRepository.get(item.payer_user_id)
        creditor_user = UserProjectionRepository.get(item.receiver_user_id)
        now = timezone.now()
        channels = list(decision.channels or [])
        channel_statuses = {channel: "PENDING" for channel in channels}
        reminder = DebtReminderRequestRepository.create(
            group_id=plan.group_id,
            settlement_plan_id=plan.id,
            settlement_plan_item_id=item.id,
            recipient_user_id=item.payer_user_id,
            creditor_user_id=item.receiver_user_id,
            requested_by_user_id=requested_by_user_id,
            sequence_number=decision.sequence_number,
            source=source,
            channels=channels,
            channel_statuses=channel_statuses,
            status=DebtReminderStatusChoices.QUEUED,
            currency=item.currency,
            amount_minor=item.amount_minor,
            source_timestamp=decision.source_timestamp,
            scheduled_at=now,
            requested_at=now,
            dedupe_key=f"{item.id}:{source}:{decision.sequence_number}",
            created_by_user_id=requested_by_user_id,
        )
        payload = self._event_payload(
            reminder,
            plan=plan,
            item=item,
            group=group,
            recipient_user=recipient_user,
            creditor_user=creditor_user,
            channels=channels,
            requested_by_user_id=requested_by_user_id,
        )
        envelope = build_event_envelope(
            "DebtReminderRequested",
            payload,
            source_service="settlement-service",
            routing_key="settlement.debt_reminder.requested",
            correlation_id=str(uuid4()),
            causation_id=str(item.id),
        )
        OutboxRepository.create(
            aggregate_type="DebtReminderRequest",
            aggregate_id=reminder.id,
            event_type="DebtReminderRequested",
            routing_key="settlement.debt_reminder.requested",
            exchange=self.exchange,
            payload=envelope,
            correlation_id=envelope["correlation_id"],
            causation_id=envelope["causation_id"],
        )
        return reminder

    @transaction.atomic
    def send_manual_item_reminder(self, item_id, user_id, payload: dict | None = None):
        payload = payload or {}
        item = SettlementPlanItemRepository.get(item_id)
        if not item:
            raise ReminderEligibilityError("Settlement plan item was not found.")
        plan = SettlementPlanRepository.get(item.settlement_plan_id)
        if not plan:
            raise ReminderEligibilityError("Settlement plan was not found.")
        member = self._active_member(plan.group_id, user_id)
        if not member or member.role not in (GroupMemberRoleChoices.OWNER, GroupMemberRoleChoices.ADMIN):
            raise ReminderPermissionDeniedError()
        requested_channels = []
        if "send_in_app" in payload or "send_email" in payload:
            if payload.get("send_in_app"):
                requested_channels.append(ReminderChannelChoices.IN_APP)
            if payload.get("send_email"):
                requested_channels.append(ReminderChannelChoices.EMAIL)
        else:
            requested_channels = None
        item = self._lock_item_queryset().filter(id=item.id).first() or item
        decision = self.evaluate_item(
            item.id,
            source=DebtReminderSourceChoices.MANUAL_ITEM,
            requested_by_user_id=user_id,
            channels_override=requested_channels,
        )
        if not decision.eligible:
            if decision.reason == "manual_cooldown":
                existing = DebtReminderRequestRepository.latest_manual_with_cooldown(
                    item.id,
                    user_id,
                    timezone.now() - timedelta(minutes=self.manual_cooldown_minutes),
                )
                if existing:
                    return existing
                raise ReminderRateLimitedError()
            raise ReminderEligibilityError(decision.reason or "manual_reminder_not_eligible")
        try:
            return self._create_reminder(
                decision,
                source=DebtReminderSourceChoices.MANUAL_ITEM,
                requested_by_user_id=user_id,
                channels_override=requested_channels,
            )
        except IntegrityError as exc:
            raise ReminderConflictError() from exc

    @transaction.atomic
    def run_group_manual(self, group_id, user_id, *, dry_run=False):
        group, member = self._group_and_member(group_id, user_id)
        ensure_can_manage_settings(member)
        items = SettlementPlanItemRepository.list_by_group(group.group_id).filter(status=SettlementPlanItemStatusChoices.PENDING)
        eligible_count = created_count = skipped_count = 0
        skip_reasons = Counter()
        for item in items.iterator():
            decision = self.evaluate_item(
                item.id,
                source=DebtReminderSourceChoices.MANUAL_GROUP_RUN,
                requested_by_user_id=user_id,
            )
            if not decision.eligible:
                skipped_count += 1
                skip_reasons[decision.reason or "skipped"] += 1
                continue
            eligible_count += 1
            if dry_run:
                continue
            try:
                locked_item = self._lock_item_queryset().filter(id=item.id).first()
                if not locked_item:
                    skipped_count += 1
                    skip_reasons["locked"] += 1
                    continue
                refreshed = self.evaluate_item(
                    locked_item.id,
                    source=DebtReminderSourceChoices.MANUAL_GROUP_RUN,
                    requested_by_user_id=user_id,
                )
                if not refreshed.eligible:
                    skipped_count += 1
                    skip_reasons[refreshed.reason or "skipped"] += 1
                    continue
                self._create_reminder(
                    refreshed,
                    source=DebtReminderSourceChoices.MANUAL_GROUP_RUN,
                    requested_by_user_id=user_id,
                )
                created_count += 1
            except IntegrityError:
                skipped_count += 1
                skip_reasons["already_created"] += 1
        return {
            "eligible_count": eligible_count,
            "created_count": created_count,
            "skipped_count": skipped_count,
            "skip_reasons": dict(skip_reasons),
        }

    def serialize_history_item(self, reminder):
        return {
            "id": str(reminder.id),
            "group_id": str(reminder.group_id),
            "recipient_user_id": str(reminder.recipient_user_id),
            "settlement_plan_item_id": str(reminder.settlement_plan_item_id),
            "sequence_number": reminder.sequence_number,
            "source": reminder.source,
            "channels": list(reminder.channels or []),
            "status": reminder.status,
            "scheduled_at": reminder.scheduled_at.isoformat() if reminder.scheduled_at else None,
            "requested_at": reminder.requested_at.isoformat() if reminder.requested_at else None,
            "sent_at": reminder.sent_at.isoformat() if reminder.sent_at else None,
            "last_error": self._safe_error(reminder.last_error),
        }

    def serialize_detail(self, reminder):
        payload = self.serialize_history_item(reminder)
        payload.update(
            {
                "creditor_user_id": str(reminder.creditor_user_id),
                "settlement_plan_id": str(reminder.settlement_plan_id),
                "item_reference": str(reminder.settlement_plan_item_id),
                "delivery_summary": reminder.channel_statuses or {},
            }
        )
        return payload

    def _safe_error(self, value):
        if not value:
            return None
        return str(value)[:255]

    def process_scheduler_batch(self):
        results = {"eligible_count": 0, "created_count": 0, "skipped_count": 0, "skip_reasons": Counter()}
        qs = SettlementPlanItemRepository.list_pending_for_scheduler(limit=self.scheduler_batch_size)
        for item in qs:
            try:
                with transaction.atomic():
                    locked_item = self._lock_item_queryset().filter(id=item.id).first()
                    if not locked_item:
                        results["skipped_count"] += 1
                        results["skip_reasons"]["locked"] += 1
                        continue
                    decision = self.evaluate_item(
                        locked_item.id,
                        source=DebtReminderSourceChoices.AUTOMATIC,
                    )
                    if not decision.eligible:
                        results["skipped_count"] += 1
                        results["skip_reasons"][decision.reason or "skipped"] += 1
                        continue
                    results["eligible_count"] += 1
                    self._create_reminder(decision, source=DebtReminderSourceChoices.AUTOMATIC)
                    results["created_count"] += 1
            except IntegrityError:
                results["skipped_count"] += 1
                results["skip_reasons"]["already_created"] += 1
            except Exception:
                results["skipped_count"] += 1
                results["skip_reasons"]["processing_failed"] += 1
        results["skip_reasons"] = dict(results["skip_reasons"])
        return results

    @transaction.atomic
    def apply_delivery_update(self, payload: dict):
        reminder = DebtReminderRequestRepository.get(payload.get("reminder_id"))
        if not reminder:
            return None
        event_timestamp = payload.get("delivery_updated_at")
        parsed_timestamp = None
        if event_timestamp:
            parsed_timestamp = datetime.fromisoformat(str(event_timestamp).replace("Z", "+00:00"))
        if reminder.delivery_updated_at and parsed_timestamp and parsed_timestamp <= reminder.delivery_updated_at:
            return reminder
        return DebtReminderRequestRepository.update_delivery(
            reminder,
            status=payload.get("status") or reminder.status,
            sent_at=parsed_timestamp if payload.get("status") == DebtReminderStatusChoices.SENT else reminder.sent_at,
            last_error=self._safe_error(payload.get("last_error")),
            channel_statuses=payload.get("channel_statuses") or reminder.channel_statuses,
            delivery_updated_at=parsed_timestamp or timezone.now(),
        )

