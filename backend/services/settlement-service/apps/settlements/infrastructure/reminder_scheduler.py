from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.settlements.domain.models import (
    GroupBalanceSnapshot,
    ManualSettlement,
    ManualSettlementStatusChoices,
    ReminderDispatchTypeChoices,
    SettlementPlan,
    SettlementPlanItem,
    SettlementPlanItemStatusChoices,
    SettlementPlanStatusChoices,
)
from apps.settlements.infrastructure.event_envelope import build_event_envelope
from apps.settlements.infrastructure.repositories import (
    GroupMemberProjectionRepository,
    GroupProjectionRepository,
    OutboxRepository,
    ReminderDispatchRepository,
)


class SettlementReminderScheduler:
    def __init__(self):
        self.enabled = settings.REMINDER_ENABLED
        self.min_interval = timedelta(hours=settings.REMINDER_MIN_INTERVAL_HOURS)
        self.exchange = settings.SETTLEMENT_RABBITMQ_EXCHANGE
        self.routing_key = "settlement.reminder.requested"

    def _reminder_context(self, group_title: str, message: str, **extra) -> dict:
        return {
            "group_title": group_title,
            "message": message,
            **{key: value for key, value in extra.items() if value is not None},
        }

    def _enqueue(self, *, reminder_type, group_id, recipient_user_id, recipient_phone_number, payload, aggregate_id=None, source_event_id=None, settlement_plan_id=None, settlement_plan_item_id=None, manual_settlement_id=None):
        now = timezone.now()
        existing = ReminderDispatchRepository.eligible(
            reminder_type, group_id, recipient_user_id
        )
        if existing and existing.next_allowed_at and existing.next_allowed_at > now:
            return None

        with transaction.atomic():
            log = ReminderDispatchRepository.upsert_target(
                reminder_type=reminder_type,
                group_id=group_id,
                settlement_plan_id=settlement_plan_id,
                settlement_plan_item_id=settlement_plan_item_id,
                manual_settlement_id=manual_settlement_id,
                recipient_user_id=recipient_user_id,
                recipient_phone_number=recipient_phone_number,
                source_event_id=source_event_id,
                next_allowed_at=now + self.min_interval,
                last_sent_at=now,
                sent_count=(existing.sent_count + 1) if existing else 1,
                metadata=payload,
            )
            envelope = build_event_envelope(
                reminder_type,
                {
                    **payload,
                    "reminder_log_id": str(log.id),
                    "recipient_phone_number": recipient_phone_number,
                },
                source_service="settlement-service",
                routing_key=self.routing_key,
            )
            outbox = OutboxRepository.create(
                aggregate_type="ReminderDispatch",
                aggregate_id=aggregate_id,
                event_type=reminder_type,
                routing_key=self.routing_key,
                exchange=self.exchange,
                payload=envelope,
                source_service="settlement-service",
                correlation_id=source_event_id,
            )
            return log, outbox

    def _group_title(self, group_id):
        group = GroupProjectionRepository.get(group_id)
        return group.title if group else "Settlement group"

    def _phone_for_user(self, group_id, user_id):
        member = GroupMemberProjectionRepository.get(group_id, user_id)
        if member and member.phone_number:
            return member.phone_number
        user = GroupMemberProjectionRepository._display_snapshot(user_id)
        if user[1]:
            return user[1]
        return None

    def enqueue_payment_reminders(self):
        if not self.enabled:
            return []

        queued = []
        active_plans = SettlementPlan.objects.filter(
            status=SettlementPlanStatusChoices.ACTIVE
        ).order_by("created_at")
        for plan in active_plans:
            group_title = self._group_title(plan.group_id)
            pending_items = SettlementPlanItem.objects.filter(
                settlement_plan_id=plan.id,
                status=SettlementPlanItemStatusChoices.PENDING,
            ).order_by("order_index", "created_at")
            for item in pending_items:
                phone_number = self._phone_for_user(plan.group_id, item.payer_user_id)
                if not phone_number:
                    continue
                payload = self._reminder_context(
                    group_title,
                    "لطفاً مبلغ این آیتم تسویه را پرداخت کنید.",
                    settlement_plan_id=str(plan.id),
                    settlement_plan_item_id=str(item.id),
                    group_id=str(plan.group_id),
                    currency=plan.currency,
                    amount_minor=item.amount_minor,
                    payer_user_id=str(item.payer_user_id),
                    receiver_user_id=str(item.receiver_user_id),
                    template_code=settings.SMS_TEMPLATE_SETTLEMENT_REMINDER,
                )
                result = self._enqueue(
                    reminder_type=ReminderDispatchTypeChoices.PAYMENT_REMINDER,
                    group_id=plan.group_id,
                    recipient_user_id=item.payer_user_id,
                    recipient_phone_number=phone_number,
                    payload=payload,
                    aggregate_id=item.id,
                    source_event_id=item.id,
                    settlement_plan_id=plan.id,
                    settlement_plan_item_id=item.id,
                )
                if result:
                    queued.append(result)
        return queued

    def enqueue_confirmation_reminders(self):
        if not self.enabled:
            return []

        queued = []
        pending_settlements = ManualSettlement.objects.filter(
            status=ManualSettlementStatusChoices.PENDING_CONFIRMATION
        ).order_by("created_at")
        for settlement in pending_settlements:
            group_title = self._group_title(settlement.group_id)
            phone_number = self._phone_for_user(
                settlement.group_id, settlement.receiver_user_id
            )
            if not phone_number:
                continue
            payload = self._reminder_context(
                group_title,
                "لطفاً تسویه ثبت‌شده را تأیید کنید.",
                manual_settlement_id=str(settlement.id),
                group_id=str(settlement.group_id),
                currency=settlement.currency,
                amount_minor=settlement.amount_minor,
                payer_user_id=str(settlement.payer_user_id),
                receiver_user_id=str(settlement.receiver_user_id),
                template_code=settings.SMS_TEMPLATE_SETTLEMENT_REMINDER,
            )
            result = self._enqueue(
                reminder_type=ReminderDispatchTypeChoices.SETTLEMENT_CONFIRMATION_REMINDER,
                group_id=settlement.group_id,
                recipient_user_id=settlement.receiver_user_id,
                recipient_phone_number=phone_number,
                payload=payload,
                aggregate_id=settlement.id,
                source_event_id=settlement.id,
                manual_settlement_id=settlement.id,
            )
            if result:
                queued.append(result)
        return queued

    def enqueue_balance_reminders(self):
        if not self.enabled:
            return []

        queued = []
        negative_balances = GroupBalanceSnapshot.objects.filter(net_balance_minor__lt=0)
        for balance in negative_balances:
            group_title = self._group_title(balance.group_id)
            phone_number = self._phone_for_user(balance.group_id, balance.user_id)
            if not phone_number:
                continue
            payload = self._reminder_context(
                group_title,
                "شما بدهی تسویه‌نشده دارید.",
                group_id=str(balance.group_id),
                user_id=str(balance.user_id),
                net_balance_minor=balance.net_balance_minor,
                currency=balance.currency,
                template_code=settings.SMS_TEMPLATE_SETTLEMENT_REMINDER,
            )
            result = self._enqueue(
                reminder_type=ReminderDispatchTypeChoices.SETTLEMENT_PLAN_ITEM_REMINDER,
                group_id=balance.group_id,
                recipient_user_id=balance.user_id,
                recipient_phone_number=phone_number,
                payload=payload,
                aggregate_id=balance.id,
                source_event_id=balance.id,
            )
            if result:
                queued.append(result)
        return queued

    def run(self):
        queued = []
        queued.extend(self.enqueue_payment_reminders())
        queued.extend(self.enqueue_confirmation_reminders())
        queued.extend(self.enqueue_balance_reminders())
        return queued
