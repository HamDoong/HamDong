# Demo Scenario

## Scenario

Ali, Sara, and Reza are in a group named **"شام جمعه"**.

## Flow

- Ali logs in.
- Sara logs in.
- Reza logs in.
- Ali creates the group.
- Ali creates an invite link.
- Sara and Reza join the group.
- Sara pays and records a `900000 IRR` expense.
- Expense is split equally between Ali, Sara, and Reza.
- System shows balances:
  - Ali = `-300000`
  - Sara = `+600000`
  - Reza = `-300000`
- System generates smart settlement plan:
  - Ali -> Sara = `300000`
  - Reza -> Sara = `300000`
- Ali reports his payment.
- Sara confirms the payment.
- Final balance:
  - Ali = `0`
  - Sara = `+300000`
  - Reza = `-300000`
- Remaining unpaid items can still trigger reminders later.

## API Sequence

1. `POST /api/v1/auth/otp/request/` for Ali, Sara, and Reza
2. `POST /api/v1/auth/otp/verify/` for Ali, Sara, and Reza
3. `POST /api/v1/groups/`
4. `POST /api/v1/groups/{group_id}/invites/`
5. `POST /api/v1/groups/invites/{token}/accept/` for Sara
6. `POST /api/v1/groups/invites/{token}/accept/` for Reza
7. `GET /api/v1/groups/{group_id}/members/`
8. optional `POST /api/v1/media/receipts/`
9. `POST /api/v1/groups/{group_id}/expenses/`
10. `GET /api/v1/groups/{group_id}/expenses/`
11. wait for async consumers
12. `GET /api/v1/groups/{group_id}/balances/`
13. `POST /api/v1/groups/{group_id}/settlement-plan/generate/`
14. `POST /api/v1/settlement-plans/{plan_id}/activate/`
15. `POST /api/v1/settlement-plan-items/{item_id}/report-paid/`
16. `POST /api/v1/settlement-plan-items/{item_id}/confirm/`
17. `GET /api/v1/groups/{group_id}/balances/`

## Presentation Tips

- Run the flow through `api-tests/hamdong.http`.
- Keep RabbitMQ consumers running before the demo.
- Mention the service boundaries and event-driven projections while waiting for async updates.
- If using local debug mode, explain that `debug_otp` exists only for demo/testing convenience and should not be enabled in production.
