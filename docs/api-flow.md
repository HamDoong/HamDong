# API Flow

Main API journey and sequence of endpoints used in demo flows.

1) Request OTP
- `POST /api/v1/auth/otp/request/` — send phone_number to receive OTP by SMS.

2) Verify OTP
- `POST /api/v1/auth/otp/verify/` — verify code, returns access and refresh tokens.

3) Create group
- `POST /api/v1/groups/` — create a new group; creator becomes owner and member.

4) Create invite
- `POST /api/v1/groups/{group_id}/invites/` — create invite token for other users.

5) Accept invite
- `POST /api/v1/groups/invites/{token}/accept/` — accepts invite and adds user to group.

6) Upload receipt
- `POST /api/v1/media/receipts/` — upload a receipt file tied to a group.

7) Create expense
- `POST /api/v1/groups/{group_id}/expenses/` — create expense with participants and amount.

8) Get balances
- `GET /api/v1/groups/{group_id}/balances/` — retrieves group balances and per-user balances.

9) Generate settlement plan
- `POST /api/v1/groups/{group_id}/settlement-plan/generate/` — generate suggested settlement plan.

10) Activate settlement plan
- `POST /api/v1/settlement-plans/{plan_id}/activate/` — activates plan to create settlement items and events.

11) Report payment
- `POST /api/v1/settlement-plan-items/{item_id}/report-paid/` — payer reports they paid.

12) Confirm payment
- `POST /api/v1/settlements/{settlement_id}/confirm/` — receiver confirms payment.

13) Get final balance
- `GET /api/v1/groups/{group_id}/balances/me/` — view personal final balance in the group.
