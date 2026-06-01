# Event Flows

This document describes main event-driven flows between services.

1) User login OTP flow
- identity-service publishes an `otp.requested` event to RabbitMQ.
- notification-service consumes `otp.requested` and creates a `NotificationJob` to send SMS via SMS provider.
- Delivery status may be logged in `ProviderDeliveryLog`.

2) User projection flow
- identity-service emits `user.created` / `user.updated` events.
- group-service, expense-service, media-service, settlement-service each consume identity events to maintain local user projections (name, phone, avatar).

3) Group membership flow
- group-service publishes `group.member.added` and `group.member.removed` events.
- expense-service, media-service, settlement-service consume these to validate permissions and update projections.

4) Expense to settlement flow
- expense-service publishes `expense.created|updated|deleted` events.
- settlement-service consumes expense events and updates debt ledger, recalculates balances.

5) Settlement reminder flow
- settlement-service schedules reminders and publishes `settlement.reminder.requested` events to RabbitMQ.
- notification-service consumes reminders and creates `NotificationJob` to send SMS reminders.

6) Smart settlement flow
- settlement-service generates a `settlement.plan.generated` event with plan items.
- plan activation and plan-item events move through the same event channels enabling consumers to update UI or send notifications.
