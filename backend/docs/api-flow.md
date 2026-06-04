# API Flow

Base URL: `http://localhost:8080`

## Request OTP

`POST /api/v1/auth/otp/request/`

Send a phone number. In local debug mode the response can include `debug_otp` for manual demo use.

## Verify OTP

`POST /api/v1/auth/otp/verify/`

Receive `access_token`, `refresh_token`, token metadata, and the current user payload.

## Create Group

`POST /api/v1/groups/`

Ali creates the group named `شام جمعه`.

## Create Invite

`POST /api/v1/groups/{group_id}/invites/`

Ali receives `invite_id` and `invite_url`. The token can be taken from the end of the URL.

## Accept Invite

`POST /api/v1/groups/invites/{token}/accept/`

Sara and Reza accept the invite with their own access tokens.

## Optional Upload Receipt

`POST /api/v1/media/receipts/`

This step is optional. Use `api-tests/fixtures/receipt.jpg` when available.

## Create Expense

`POST /api/v1/groups/{group_id}/expenses/`

Sara creates the `900000 IRR` equal-split expense using:

- `base_amount_minor`
- `payer_user_id`
- `split_method`
- `participant_user_ids`
- `tax_type`
- `service_fee_type`

## Get Balances

`GET /api/v1/groups/{group_id}/balances/`

Wait briefly after creating the expense so async projections can catch up.

## Generate Settlement Plan

`POST /api/v1/groups/{group_id}/settlement-plan/generate/`

Receive a settlement-plan payload with `id` and `items[]`.

## Activate Settlement Plan

`POST /api/v1/settlement-plans/{plan_id}/activate/`

Ali activates the generated plan.

## Report Payment

`POST /api/v1/settlement-plan-items/{item_id}/report-paid/`

Ali reports his payment and receives `manual_settlement_id`.

## Confirm Payment

`POST /api/v1/settlement-plan-items/{item_id}/confirm/`

Sara confirms the reported payment.

## Get Final Balances

`GET /api/v1/groups/{group_id}/balances/`

The final response should show Ali settled and one remaining unpaid Reza debt.
