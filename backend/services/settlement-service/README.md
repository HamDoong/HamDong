# settlement-service (Phases 7 and 8)

Settlement-service is the projection and workflow engine for group balances, debt ledger history, manual settlement lifecycle, and smart settlement planning.

## Overview

- Reads identity, group, and expense domain events from RabbitMQ.
- Builds local read/write projections in settlement DB only.
- Computes auditable debt and balance state from ledger entries.
- Manages manual settlement request/confirm/reject/cancel flows.
- Generates deterministic debt simplification plans from group balances.
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

## Phase 8 Smart Settlement

Phase 8 adds settlement plans that simplify balances into fewer transactions without changing expense calculation or introducing payments.

### Core Concept

- Input: latest `GroupBalanceSnapshot` rows for a group.
- Output: `SettlementPlan` and `SettlementPlanItem` rows.
- Positive balance means creditor.
- Negative balance means debtor.
- All money stays in integer minor units.

### Plan Lifecycle

- `DRAFT`: generated but not active yet.
- `ACTIVE`: members can report and confirm items.
- `COMPLETED`: all plan items are confirmed.
- `CANCELLED`: the plan was cancelled.
- `EXPIRED`: balances changed after the plan was generated.

### Item Lifecycle

- `PENDING`: waiting for the payer to report payment.
- `REPORTED`: payer reported the payment.
- `CONFIRMED`: receiver confirmed the payment.
- `REJECTED`: receiver rejected the payment.
- `CANCELLED`: item was cancelled with the plan or as part of plan cancellation.

### Debt Simplification Algorithm

- Separate debtors and creditors.
- Sort debtors by largest absolute debt first.
- Sort creditors by largest credit first.
- Match them with a two-pointer walk.
- Create one plan item per match using `min(abs(debtor), creditor)`.
- Skip zero-amount items.
- Never create payer and receiver as the same user.
- Output is deterministic.

### Permission Rules

- Only `OWNER` or `ADMIN` can generate, activate, or cancel a plan.
- Only active group members can view the latest plan.
- Only the payer can report a plan item as paid.
- Only the receiver can confirm or reject a reported item.

### Manual Settlement Integration

- Reporting a plan item creates a Phase 7 `ManualSettlement` in `PENDING_CONFIRMATION`.
- Confirming a plan item reuses the Phase 7 manual settlement confirmation logic.
- Rejecting a plan item reuses the Phase 7 manual settlement rejection logic.
- Confirming a plan item recalculates the group balance using the existing balance service.

### Settlement Plan Events

- Exchange: `hamdong.settlement`
- Routing keys:
	- `settlement.plan.generated`
	- `settlement.plan.activated`
	- `settlement.plan.cancelled`
	- `settlement.plan.expired`
	- `settlement.plan.completed`
	- `settlement.plan_item.reported`
	- `settlement.plan_item.confirmed`
	- `settlement.plan_item.rejected`

## Event Consumption

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
	- `settlement.plan.generated`
	- `settlement.plan.activated`
	- `settlement.plan.cancelled`
	- `settlement.plan.expired`
	- `settlement.plan.completed`
	- `settlement.plan_item.reported`
	- `settlement.plan_item.confirmed`
	- `settlement.plan_item.rejected`
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
- `POST /api/v1/groups/{group_id}/settlement-plan/generate/`
- `GET /api/v1/groups/{group_id}/settlement-plan/`
- `POST /api/v1/settlement-plans/{plan_id}/activate/`
- `POST /api/v1/settlement-plans/{plan_id}/cancel/`
- `POST /api/v1/settlement-plan-items/{item_id}/report-paid/`
- `POST /api/v1/settlement-plan-items/{item_id}/confirm/`
- `POST /api/v1/settlement-plan-items/{item_id}/reject/`

## Testing Commands

- `pytest apps/settlements/tests/test_phase7.py -q`
- `pytest apps/settlements/tests/test_settlement_plan_algorithm.py -q`
- `pytest apps/settlements/tests/test_generate_settlement_plan.py -q`
- `pytest apps/settlements/tests/test_activate_settlement_plan.py -q`
- `pytest apps/settlements/tests/test_report_plan_item.py -q`
- `pytest apps/settlements/tests/test_complete_settlement_plan.py -q`
- `pytest -q`
- `python manage.py check`
- `python manage.py migrate --noinput`

## Exclusions in Phases 7 and 8

Phases 7 and 8 intentionally do not implement:

- online payment
- wallet
- payment gateway
- bank callback
- reminders
- frontend
- changes to expense calculation
- changes to media-service
