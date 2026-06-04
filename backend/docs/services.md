# Services

## identity-service

**Responsibility**
- OTP authentication
- access/refresh token issuance
- JWKS/public key exposure
- current-user profile APIs

**Database**
- `identity_db`

**Main endpoints**
- `POST /api/v1/auth/otp/request/`
- `POST /api/v1/auth/otp/verify/`
- `POST /api/v1/auth/token/refresh/`
- `POST /api/v1/auth/logout/`
- `GET /api/v1/users/me/`
- `PATCH /api/v1/users/me/`
- `GET /api/v1/auth/jwks/`
- `GET /api/v1/auth/.well-known/jwks.json/`
- `GET /api/v1/auth/health/`

**Input events**
- none as a source of truth service

**Output events**
- `UserCreated`
- `UserUpdated`
- `UserLoggedIn`
- `SendOtpSmsRequested`

**Consumers**
- none for core identity domain events

**Dispatchers**
- `python manage.py dispatch_outbox`

## notification-service

**Responsibility**
- send OTP SMS
- send reminder SMS
- store notification jobs
- track delivery success/failure

**Database**
- `notification_db`

**Main endpoints**
- `GET /api/v1/notifications/health/`
- `POST /api/v1/notifications/sms/test/`
- `GET /api/v1/notifications/messages/`

**Input events**
- `SendOtpSmsRequested`
- `PaymentReminderRequested`
- `SettlementConfirmationReminderRequested`
- `SettlementPlanItemReminderRequested`

**Output events**
- `NotificationSent`
- `NotificationFailed`
- `SmsSent`
- `SmsFailed`

**Consumers**
- `python manage.py consume_notification_events`

**Dispatchers**
- `python manage.py dispatch_outbox`

## group-service

**Responsibility**
- group create/update/archive
- membership and invite lifecycle
- owner/member permissions

**Database**
- `group_db`

**Main endpoints**
- `POST /api/v1/groups/`
- `GET /api/v1/groups/`
- `GET /api/v1/groups/{group_id}/`
- `PATCH /api/v1/groups/{group_id}/`
- `POST /api/v1/groups/{group_id}/archive/`
- `GET /api/v1/groups/{group_id}/members/`
- `POST /api/v1/groups/{group_id}/members/{member_id}/remove/`
- `POST /api/v1/groups/{group_id}/leave/`
- `POST /api/v1/groups/{group_id}/invites/`
- `GET /api/v1/groups/invites/{token}/`
- `POST /api/v1/groups/invites/{token}/accept/`
- `POST /api/v1/groups/{group_id}/invites/{invite_id}/revoke/`
- `GET /api/v1/groups/health/`

**Input events**
- identity user projection events

**Output events**
- `GroupCreated`
- `GroupUpdated`
- `GroupArchived`
- `GroupInviteCreated`
- `GroupInviteAccepted`
- `GroupMemberJoined`
- `GroupMemberRemoved`
- `GroupMemberLeft`

**Consumers**
- identity event consumers

**Dispatchers**
- `python manage.py dispatch_outbox`

## expense-service

**Responsibility**
- expense write model
- split calculations
- expense participant persistence
- expense events for projections

**Database**
- `expense_db`

**Main endpoints**
- `POST /api/v1/groups/{group_id}/expenses/`
- `GET /api/v1/groups/{group_id}/expenses/`
- `GET /api/v1/expenses/{expense_id}/`
- `PATCH /api/v1/expenses/{expense_id}/`
- `DELETE /api/v1/expenses/{expense_id}/`
- `GET /api/v1/expenses/health/`

**Input events**
- identity user events
- group membership events

**Output events**
- `ExpenseCreated`
- `ExpenseUpdated`
- `ExpenseDeleted`
- `ExpenseParticipantsChanged`

**Consumers**
- identity/group projection consumers

**Dispatchers**
- `python manage.py dispatch_outbox`

## media-service

**Responsibility**
- receipt upload metadata
- secure file download
- group media listing
- media deletion

**Database**
- `media_db`

**Main endpoints**
- `POST /api/v1/media/receipts/`
- `GET /api/v1/media/files/{file_id}/`
- `GET /api/v1/media/files/{file_id}/download/`
- `GET /api/v1/groups/{group_id}/media/`
- `DELETE /api/v1/media/files/{file_id}/`
- `GET /api/v1/media/health/`

**Input events**
- identity user events
- group membership/group lifecycle events

**Output events**
- `MediaUploaded`
- `MediaDeleted`

**Consumers**
- identity/group projection consumers

**Dispatchers**
- `python manage.py dispatch_outbox`

## settlement-service

**Responsibility**
- group balance and debt projections
- manual settlement workflow
- smart settlement plan generation and activation
- reminder scheduling

**Database**
- `settlement_db`

**Main endpoints**
- `GET /api/v1/groups/{group_id}/balances/`
- `GET /api/v1/groups/{group_id}/balances/me/`
- `GET /api/v1/groups/{group_id}/debts/`
- `POST /api/v1/groups/{group_id}/settlements/`
- `GET /api/v1/groups/{group_id}/settlements/`
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
- `GET /api/v1/settlements/health/`

**Input events**
- identity user events
- group membership events
- expense events

**Output events**
- `SettlementCreated`
- `SettlementConfirmed`
- `SettlementRejected`
- `SettlementCancelled`
- `BalanceRecalculated`
- `DebtLedgerUpdated`
- `SettlementPlanGenerated`
- `SettlementPlanActivated`
- `SettlementPlanCompleted`
- `PaymentReminderRequested`
- `SettlementConfirmationReminderRequested`
- `SettlementPlanItemReminderRequested`

**Consumers**
- identity/group/expense consumers
- reminder scheduler command

**Dispatchers**
- `python manage.py dispatch_outbox`
- `python manage.py run_reminder_scheduler`
