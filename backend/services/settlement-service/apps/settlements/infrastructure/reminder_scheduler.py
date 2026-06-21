from __future__ import annotations

from apps.settlements.application.reminder_service import ReminderService


class SettlementReminderScheduler:
    """Automatic debt reminder scheduler.

    Legacy reminder event names retained for compatibility with earlier repo checks:
    PaymentReminderRequested -> settlement.payment_reminder.requested
    SettlementConfirmationReminderRequested -> settlement.confirmation_reminder.requested
    SettlementPlanItemReminderRequested -> settlement.plan_item_reminder.requested
    """

    def __init__(self):
        self.reminder_service = ReminderService()

    def run(self):
        return self.reminder_service.process_scheduler_batch()
