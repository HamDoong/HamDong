# Event Flow

## OTP Login Flow

1. Client requests OTP through identity-service.
2. identity-service stores an OTP hash with expiration and writes `SendOtpSmsRequested` to outbox.
3. `identity-outbox-dispatcher` publishes the event to `hamdong.identity`.
4. notification-service consumes it, records idempotency, sends SMS, and records notification status.

Example:

```text
identity-service -> hamdong.identity -> notification-service
```

## User Projection Flow

After login or profile update, identity-service emits user events. group-service, expense-service, media-service, and settlement-service consume the events and update local user projections.

```text
identity-service -> hamdong.identity -> group/expense/media/settlement services
```

## Group Membership Flow

group-service emits membership and invite events. expense-service, media-service, and settlement-service consume them to keep membership projections current.

```text
group-service -> hamdong.group -> expense/media/settlement services
```

## Expense to Settlement Flow

expense-service emits `ExpenseCreated`, `ExpenseUpdated`, and `ExpenseDeleted`. settlement-service consumes those events, updates expense projections, debt ledgers, and balance snapshots.

```text
expense-service -> hamdong.expense -> settlement-service
```

## Settlement Plan Flow

settlement-service calculates plans from balances, stores plan records, and emits plan lifecycle events such as `SettlementPlanGenerated`, `SettlementPlanActivated`, and `SettlementPlanCompleted`.

## Reminder Flow

settlement-service identifies overdue balances, pending settlement confirmations, or active plan items. It emits reminder request events. notification-service consumes them, creates `NotificationJob`, renders the SMS template, and sends the message.

```text
settlement-service -> hamdong.settlement -> notification-service
```

## Outbox/Inbox Flow

1. Business transaction writes domain data and an `OutboxMessage`.
2. Dispatcher publishes pending outbox rows.
3. Consumer validates the event envelope.
4. Consumer checks `InboxMessage` or `ProcessedEvent`.
5. New events are processed; duplicate `event_id` values are skipped.

## Retry/DLQ Flow

Outbox dispatch failures increment retry counters and store `last_error`. Consumers use configured retry or failed-message handling so poison messages do not loop endlessly. Important queues have DLQ names documented through configuration.
