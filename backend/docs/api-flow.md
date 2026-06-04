# API Flow

## OTP Login Flow

1. `POST /api/v1/auth/otp/request/`
2. `POST /api/v1/auth/otp/verify/`
3. Save `access_token`, `refresh_token`, and `user.id`

## User Profile Flow

1. `GET /api/v1/users/me/`
2. `PATCH /api/v1/users/me/`

## Group / Invite Flow

1. `POST /api/v1/groups/`
2. `GET /api/v1/groups/`
3. `POST /api/v1/groups/{group_id}/invites/`
4. `GET /api/v1/groups/invites/{token}/`
5. `POST /api/v1/groups/invites/{token}/accept/`
6. `GET /api/v1/groups/{group_id}/members/`

## Expense Flow

1. `POST /api/v1/groups/{group_id}/expenses/`
2. `GET /api/v1/groups/{group_id}/expenses/`
3. `GET /api/v1/expenses/{expense_id}/`
4. `PATCH /api/v1/expenses/{expense_id}/`
5. `DELETE /api/v1/expenses/{expense_id}/`

Important payload contract:
- `base_amount_minor`
- `payer_user_id`
- `split_method`
- `participant_user_ids`
- `participants[].base_share_minor`
- `tax_type`
- `tax_percentage` / `tax_amount_minor`
- `service_fee_type`
- `service_fee_percentage` / `service_fee_amount_minor`

Deprecated fields are intentionally not used:
- `amount`
- `paid_by`
- `paidBy`

## Media Flow

1. `POST /api/v1/media/receipts/`
2. `GET /api/v1/media/files/{file_id}/`
3. `GET /api/v1/media/files/{file_id}/download/`
4. `GET /api/v1/groups/{group_id}/media/`
5. `DELETE /api/v1/media/files/{file_id}/`

## Settlement Flow

1. `GET /api/v1/groups/{group_id}/balances/`
2. `GET /api/v1/groups/{group_id}/balances/me/`
3. `GET /api/v1/groups/{group_id}/debts/`
4. `POST /api/v1/groups/{group_id}/settlements/`
5. `GET /api/v1/groups/{group_id}/settlements/`
6. `POST /api/v1/settlements/{settlement_id}/confirm/`
7. `POST /api/v1/settlements/{settlement_id}/reject/`
8. `POST /api/v1/settlements/{settlement_id}/cancel/`

## Smart Settlement Flow

1. `POST /api/v1/groups/{group_id}/settlement-plan/generate/`
2. `GET /api/v1/groups/{group_id}/settlement-plan/`
3. `POST /api/v1/settlement-plans/{plan_id}/activate/`
4. `POST /api/v1/settlement-plans/{plan_id}/cancel/`
5. `POST /api/v1/settlement-plan-items/{item_id}/report-paid/`
6. `POST /api/v1/settlement-plan-items/{item_id}/confirm/`
7. `POST /api/v1/settlement-plan-items/{item_id}/reject/`

## Notification Flow

1. `GET /api/v1/notifications/health/`
2. `POST /api/v1/notifications/sms/test/` in local/debug scenarios
3. `GET /api/v1/notifications/messages/`

## Demo Execution Flow

The end-to-end REST Client walkthrough is encoded in `api-tests/hamdong.http` and mirrors the same sequence used in the demo scenario document.
