# API Flow

Base URL: `http://localhost:8080`

## Request OTP

`POST /api/v1/auth/otp/request/`

The client sends a phone number. In local debug mode, the response can include `debug_otp`.

## Verify OTP

`POST /api/v1/auth/otp/verify/`

The client receives access and refresh tokens.

## Create Group

`POST /api/v1/groups/`

Ali creates the group named `شام جمعه`.

## Create Invite

`POST /api/v1/groups/{group_id}/invites/`

Ali creates an invite link or token.

## Accept Invite

`POST /api/v1/groups/invites/{token}/accept/`

Sara and Reza accept the invite with their own access tokens.

## Upload Receipt

`POST /api/v1/media/receipts/`

This step is optional for the demo. It requires a multipart file fixture such as `api-tests/fixtures/receipt.jpg`.

## Create Expense

`POST /api/v1/groups/{group_id}/expenses/`

Sara creates the 900000 IRR equal split expense using `base_amount_minor`, `payer_user_id`, `split_method`, and `participant_user_ids`.

## Get Balances

`GET /api/v1/groups/{group_id}/balances/`

Wait a few seconds after creating an expense so RabbitMQ consumers can update settlement projections.

## Generate Settlement Plan

`POST /api/v1/groups/{group_id}/settlement-plan/generate/`

settlement-service creates an optimized plan.

## Activate Settlement Plan

`POST /api/v1/settlement-plans/{plan_id}/activate/`

The plan becomes active.

## Report Payment

`POST /api/v1/settlement-plan-items/{item_id}/report-paid/`

Ali reports his payment.

## Confirm Payment

`POST /api/v1/settlement-plan-items/{item_id}/confirm/`

Sara confirms receipt.

## Get Final Balances

`GET /api/v1/groups/{group_id}/balances/`

The final balance reflects confirmed payment.
