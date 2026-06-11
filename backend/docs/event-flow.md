# Event Flow

## OTP Login Flow

1. Client calls identity-service to request an OTP.
2. identity-service hashes the OTP, stores expiration/cooldown state, and writes `SendOtpSmsRequested` to the outbox.
3. `identity-outbox-dispatcher` publishes the event to the `hamdong.identity` exchange.
4. notification-service consumes the event, records inbox state, sends the OTP SMS, and stores delivery status.

```text
identity-service -> hamdong.identity -> notification-service
```

## User Projection Flow

1. A user is created or updated in identity-service.
2. identity-service emits user events through `hamdong.identity`.
3. group-service, expense-service, media-service, and settlement-service consume the event and update their local user projection tables.

```text
identity-service -> hamdong.identity -> group/expense/media/settlement services
```

## Group Membership Flow

1. group-service creates a group invite or accepts an invite.
2. group-service emits membership events through `hamdong.group`.
3. expense-service, media-service, and settlement-service update group/member projections so they can authorize later requests without direct group DB reads.

```text
group-service -> hamdong.group -> expense/media/settlement services
```

## Expense to Settlement Flow

1. expense-service validates the expense payload and stores the expense.
2. expense-service writes `ExpenseCreated`, `ExpenseUpdated`, or `ExpenseDeleted` to the outbox.
3. `expense-outbox-dispatcher` publishes to `hamdong.expense`.
4. settlement-service consumes the event, updates expense projections, recalculates balances/debts, and stores new snapshots.

```text
expense-service -> hamdong.expense -> settlement-service
```

## Settlement Plan Flow

1. settlement-service calculates a minimized plan from current balances.
2. It stores a settlement plan plus ordered plan items.
3. It emits plan lifecycle events such as `SettlementPlanGenerated`, `SettlementPlanActivated`, `SettlementPlanCancelled`, and `SettlementPlanCompleted`.
4. Clients then report and confirm plan-item payments through synchronous API calls while the service keeps emitting lifecycle events.

## Reminder Flow

1. `settlement-reminder-scheduler` scans for overdue balances, pending manual settlements, and active plan items that need reminders.
2. settlement-service writes reminder request events to the outbox.
3. `settlement-outbox-dispatcher` publishes them to `hamdong.settlement`.
4. notification-service consumes the reminder request, creates a `NotificationJob`, renders the message, and sends the SMS.

```text
settlement-service -> hamdong.settlement -> notification-service
```

## Outbox/Inbox Flow

1. A business transaction stores domain data and an `OutboxMessage` in the same database transaction.
2. A dispatcher process fetches available outbox rows, publishes them, and marks them published or failed.
3. Consumers validate the event envelope and check `InboxMessage` or processed-event state.
4. New events are processed once; duplicate `event_id` values are acknowledged and skipped.

## Retry / DLQ Flow

- Outbox dispatch failures increment retry counters and keep `last_error`.
- `EVENT_RETRY_DELAY_SECONDS` controls backoff windows for republishing.
- `EVENT_MAX_RETRY_COUNT` limits repeated attempts.
- Queue-specific DLQ names such as `*.dlq` isolate poison messages so they do not loop forever.
- Operators should inspect DLQ messages before replaying them.

## Practical Async Notes

- After invite acceptance, wait briefly before creating expenses if downstream member projections are still catching up.
- After expense creation, wait briefly before checking balances or generating a plan.
- After reporting a plan item as paid, wait for the synchronous response with `manual_settlement_id`, then confirm the item from the receiver account.
