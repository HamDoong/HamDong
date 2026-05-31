# settlement-service (Phase 7)

Settlement-service is the projection and workflow engine for group balances, debt ledger history, and manual settlement lifecycle.

## Phase 7 Overview

- Reads identity, group, and expense domain events from RabbitMQ.
- Builds local read/write projections in settlement DB only.
- Computes auditable debt and balance state from ledger entries.
- Manages manual settlement request/confirm/reject/cancel flows.
- Publishes settlement-domain events for downstream consumers.

## Architecture

- API Layer: DRF views and serializers for balance/debt/settlement endpoints.
- Application Layer: debt, balance, settlement, and recalculation services.
- Domain Layer: event types, business rules, and status/value semantics.
- Infrastructure Layer: RabbitMQ consumer/publisher, JWT/JWKS auth, repositories.

## Projection Strategy

- `UserProjection`, `GroupProjection`, `GroupMemberProjection` are materialized from identity/group events.
- `ExpenseProjection` and `ExpenseParticipantProjection` are materialized from expense events.
- `DebtLedgerEntry` is append-only/audit-friendly; updates are reversals, not deletes.
- `GroupBalanceSnapshot` stores latest per-user computed group balances.
- `ProcessedEvent` guarantees idempotent event consumption by `event_id`.

## Event Consumption

### Identity Events

- Consumes `UserCreated`, `UserUpdated`.
- Updates `UserProjection`.
- Queue: `SETTLEMENT_IDENTITY_QUEUE`.

### Group Events

- Consumes `GroupCreated`, `GroupUpdated`, `GroupArchived`, `GroupMemberJoined`, `GroupMemberRemoved`, `GroupMemberLeft`.
- Updates `GroupProjection` and `GroupMemberProjection`.
- Queue: `SETTLEMENT_GROUP_QUEUE`.

### Expense Events

- Consumes `ExpenseCreated`, `ExpenseUpdated`, `ExpenseDeleted`, `ExpenseParticipantsChanged`.
- Updates expense projections, debt ledger, and balance snapshots.
- Queue: `SETTLEMENT_EXPENSE_QUEUE`.

## Debt Ledger Rules

- Money is stored in minor integer units.
- Currency defaults to `IRR`.
- On expense create: create active `EXPENSE_SHARE` entries for non-payer participants only.
- On expense update: reverse prior active entries and create new active entries.
- On expense delete: reverse active entries.
- Reversed entries are retained for audit and never physically deleted.

## Balance Calculation Rules

- Computation uses ACTIVE ledger rows only.
- Debt row (`debtor -> creditor`) effect:
	- debtor net decreases by amount
	- creditor net increases by amount
- Confirmed manual settlement (`payer -> receiver`) effect:
	- payer net increases by amount
	- receiver net decreases by amount
- Status mapping:
	- positive: `CREDITOR`
	- negative: `DEBTOR`
	- zero: `SETTLED`

## Manual Settlement Workflow

- `POST /api/v1/groups/{group_id}/settlements/` creates `PENDING_CONFIRMATION` records.
- `POST /api/v1/settlements/{settlement_id}/confirm/` confirms by receiver only.
- `POST /api/v1/settlements/{settlement_id}/reject/` rejects by receiver only.
- `POST /api/v1/settlements/{settlement_id}/cancel/` cancels by payer only.
- Non-pending settlements are immutable for these actions.

## Idempotency

- Every consumable event envelope includes `event_id`.
- `ProcessedEvent` stores consumed IDs and prevents double application.
- Duplicate messages are skipped safely.

## Settlement Event Publishing

- Exchange: `hamdong.settlement`.
- Routing keys:
	- `settlement.created`
	- `settlement.confirmed`
	- `settlement.rejected`
	- `settlement.cancelled`
	- `settlement.balance_recalculated`
	- `settlement.debt_ledger_updated`
- Envelope fields are consistent and versioned:
	- `event_id`
	- `event_type`
	- `occurred_at`
	- `version`
	- `data`

## Docker Compose Usage

- API service: `settlement-service`
- Consumer service: `settlement-consumer`
- Preferred consumer command: `python manage.py consume_events`
- Optional split commands:
	- `python manage.py consume_identity_events`
	- `python manage.py consume_group_events`
	- `python manage.py consume_expense_events`

## Endpoint Examples

- `GET /api/v1/groups/{group_id}/balances/`
- `GET /api/v1/groups/{group_id}/balances/me/`
- `GET /api/v1/groups/{group_id}/debts/`
- `GET /api/v1/groups/{group_id}/settlements/?status=PENDING_CONFIRMATION`
- `POST /api/v1/groups/{group_id}/settlements/`
- `POST /api/v1/settlements/{settlement_id}/confirm/`
- `POST /api/v1/settlements/{settlement_id}/reject/`
- `POST /api/v1/settlements/{settlement_id}/cancel/`

## Testing Commands

- `pytest apps/settlements/tests/test_phase7.py -q`
- `python manage.py check`
- `python manage.py migrate --noinput`

## Exclusions in Phase 7

Phase 7 intentionally does not implement:

- smart settlement
- optimized settlement plans
- minimum transaction calculation
- wallet
- payment gateway
- online payment
- reminders
- frontend