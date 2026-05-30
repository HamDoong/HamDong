# Expense Service (Phase 5)

Overview
- Implements expense tracking for groups: create, list, detail, update, soft-delete.
- Event-driven projections for users and groups (consumes identity & group events).

Key concepts
- Projections: `UserProjection`, `GroupProjection`, `GroupMemberProjection` provide local read models.
- Money: stored as integer minor units (no floats).
- Splits: `EQUAL` and `CUSTOM_AMOUNT`. Equal uses deterministic remainder distribution.
- Tax & Service Fee: supported as `NONE`, `PERCENTAGE`, or `FIXED`. Totals calculated in minor units and distributed proportionally by base share.
- Events published to exchange `hamdong.expense` with routing keys `expense.created`, `expense.updated`, `expense.deleted`, `expense.participants_changed`.

Consumers
- `python manage.py consume_events` starts identity and group consumers that update projections.

Excluded from Phase 5
- Receipt upload/media storage, settlement/payment/wallet, reminders, frontend UI, debt ledger.

Running locally
1. Configure `.env` (see `backend/.env.example`).
2. Start services via `docker-compose up --build`.

Testing
- Unit tests for rounding/tax/distribution are in `apps/expenses/tests/`.
