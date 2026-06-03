# Fix Pack 5 Report

Implemented against the uploaded HamDong Fix Pack 5 instructions. 

## Services with `OutboxMessage`
- identity-service
- group-service
- expense-service
- media-service
- settlement-service
- notification-service

## Services with `InboxMessage` or `ProcessedEvent`
- group-service: `InboxMessage`
- expense-service: `InboxMessage`
- media-service: `InboxMessage`
- settlement-service: `ProcessedEvent` and `InboxMessage` (kept `ProcessedEvent` for backward compatibility)
- notification-service: `InboxMessage`

## `dispatch_outbox` command locations
- `services/identity-service/apps/identity/management/commands/dispatch_outbox.py`
- `services/group-service/apps/groups/management/commands/dispatch_outbox.py`
- `services/expense-service/apps/expenses/management/commands/dispatch_outbox.py`
- `services/media-service/apps/media_files/management/commands/dispatch_outbox.py`
- `services/settlement-service/apps/settlements/management/commands/dispatch_outbox.py`
- `services/notification-service/apps/notifications/management/commands/dispatch_outbox.py`

## Contract files added or updated
- `shared/contracts/schemas/event_envelope.schema.json`
- `shared/contracts/events/identity.events.json`
- `shared/contracts/events/group.events.json`
- `shared/contracts/events/expense.events.json`
- `shared/contracts/events/media.events.json`
- `shared/contracts/events/settlement.events.json`
- `shared/contracts/events/notification.events.json`

## Reminder flow
- `settlement-service` now owns reminder generation in `apps/settlements/infrastructure/reminder_scheduler.py`.
- The scheduler emits:
  - `PaymentReminderRequested`
  - `SettlementConfirmationReminderRequested`
  - `SettlementPlanItemReminderRequested`
- Reminder events are wrapped in the standard event envelope and persisted through `OutboxMessage`.
- Duplicate reminder suppression is handled with `ReminderDispatchLog` and `REMINDER_MIN_INTERVAL_HOURS`.
- `notification-service` consumes reminder events in `apps/notifications/infrastructure/reminder_consumer.py`.
- The consumer validates the event envelope, uses `InboxMessage` idempotency, creates `NotificationJob`, renders the SMS body, and sends through the existing `SmsService`, which keeps the current SMS circuit breaker path.

## Retry and DLQ configuration
- Added/normalized outbox env support:
  - `EVENT_OUTBOX_BATCH_SIZE`
  - `EVENT_OUTBOX_POLL_INTERVAL_SECONDS`
  - `EVENT_MAX_RETRY_COUNT`
  - `EVENT_DLQ_SUFFIX`
  - `EVENT_RETRY_DELAY_SECONDS`
- All producer services now have `dispatch_outbox` dispatchers.
- `docker-compose.yml` now includes:
  - `identity-outbox-dispatcher`
  - `group-outbox-dispatcher`
  - `expense-outbox-dispatcher`
  - `media-outbox-dispatcher`
  - `settlement-outbox-dispatcher`
  - `notification-outbox-dispatcher`
  - `settlement-reminder-scheduler`
  - `notification-reminder-consumer`
- Consumer queue declarations use dead-letter queue suffixing via `EVENT_DLQ_SUFFIX`.
- Outbox dispatchers retry by keeping messages retryable until `EVENT_MAX_RETRY_COUNT`, then leaving them in `FAILED`.

## Code fixes beyond the initial outbox plumbing
- Normalized settlement outbox repository behavior to use `PENDING / PUBLISHED / FAILED`.
- Added `event_version` persistence to settlement outbox.
- Added manual migrations for outbox/inbox changes across all affected services.
- Updated `notification-service` identity consumer wrapper to use the idempotent envelope-validating consumer.
- Cleaned expense event consumer commands so they run the actual combined consumers instead of mixed placeholder code.
- Updated shared event contracts so settlement/group contracts match the routing keys that code actually emits.

## Tests run and results
### Static verification run locally in this sandbox
- `python -m compileall services tests`
  - Result: passed
- `python -m pytest tests/test_fixpack5_phase9.py -q`
  - Result: `8 passed`

### What these tests cover
- event envelope schema validation and failure cases
- contract file existence and non-empty definitions
- settlement/group routing keys aligned between contracts and code
- presence of outbox/inbox models and dispatcher commands
- reminder scheduler and reminder consumer wiring
- docker-compose worker definitions
- no Makefile introduced

## Remaining known issues
- Full Django/database migration execution was not run here because Django is not installed in this sandbox runtime.
- Full RabbitMQ/Postgres integration was not run here because Docker Compose is unavailable in this sandbox runtime.
- Migrations were added manually and should be exercised in the project containers with `migrate` before production use.
- `settlement-service` retains both `ProcessedEvent` and `InboxMessage` to avoid broad cleanup during this pack.
- This pack does not change gateway, demo flow, JWT/auth fixes, expense duplicate handling, or other out-of-scope areas.
