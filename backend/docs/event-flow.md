# Event Flow

## OTP Login Flow

1. Client calls `POST /api/v1/auth/otp/request/`.
2. identity-service generates OTP, stores a hashed value with TTL/rate-limit metadata, and creates an outbox event for `SendOtpSmsRequested`.
3. `dispatch_outbox` publishes the envelope to RabbitMQ.
4. notification-service consumes the event, validates the envelope, deduplicates via `InboxMessage`, creates a `NotificationJob`, and sends the OTP SMS.
5. Client verifies OTP through `POST /api/v1/auth/otp/verify/`.
6. identity-service issues RS256 access and refresh tokens and emits login-related user events as needed.

## User Projection Flow

- identity-service publishes `UserCreated` and `UserUpdated`.
- group-service, expense-service, media-service, and settlement-service consume those events.
- Each consumer validates the envelope and writes or updates local projections only in its own database.

## Group Membership Flow

- group-service publishes `GroupCreated`, `GroupInviteAccepted`, `GroupMemberJoined`, `GroupMemberRemoved`, and `GroupMemberLeft`.
- expense-service, media-service, and settlement-service consume these events to maintain local group/member projections.
- Duplicate delivery is ignored using `InboxMessage` / `ProcessedEvent`.

## Expense to Settlement Flow

1. expense-service stores an expense and participants.
2. It creates `ExpenseCreated` or `ExpenseUpdated` in the outbox.
3. settlement-service consumes the event.
4. settlement-service updates `ExpenseProjection`, recomputes `DebtLedgerEntry`, and refreshes balance snapshots.
5. Duplicate expense events do not create duplicate debt ledger side effects.

## Settlement Plan Flow

1. A client requests smart settlement generation.
2. settlement-service reads current balances and creates a deterministic plan.
3. The activated plan produces plan items for debtor/creditor payment steps.
4. Members can report-paid, confirm, or reject plan items.
5. Related settlement events are published through the outbox.

## Reminder Flow

1. `run_reminder_scheduler` checks:
   - negative balances above threshold
   - old pending manual settlements
   - eligible active plan items
2. For each eligible reminder, settlement-service creates a `ReminderDispatchLog` and stores reminder request events in `OutboxMessage`.
3. `dispatch_outbox` publishes those reminder events.
4. notification-service consumes them, creates `NotificationJob`, renders the correct SMS template, and sends the SMS via the existing provider and circuit breaker.
5. Duplicate reminder events with the same `event_id` do not create duplicate jobs.

## Outbox / Inbox Flow

- Business write occurs.
- A standard event envelope is stored in `OutboxMessage`.
- `dispatch_outbox` publishes pending rows.
- Consumer receives the message.
- Consumer validates the envelope against the shared contract.
- Consumer checks `InboxMessage` / `ProcessedEvent`.
- If already processed, it skips safely.
- If new, it applies the projection/update and marks the inbox row as processed.

## Retry / DLQ Flow

- Outbox retries use `retry_count`, `last_error`, `EVENT_MAX_RETRY_COUNT`, and retry delay settings.
- Consumers are designed not to crash permanently because of one bad event.
- Failed or poison-message handling is controlled either by failed-message status in the database or by RabbitMQ DLQ configuration for important queues.
- Important DLQ names are documented in Fix Pack 5 and reflected by queue configuration/environment settings.
