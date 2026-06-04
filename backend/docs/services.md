# Services

## identity-service

- Responsibility: OTP login, user profiles, JWT issuing, refresh/logout, JWKS.
- Database: identity database.
- Main endpoints: `/api/v1/auth/otp/request/`, `/api/v1/auth/otp/verify/`, `/api/v1/auth/token/refresh/`, `/api/v1/auth/logout/`, `/api/v1/users/me/`, `/api/v1/auth/jwks/`, `/api/v1/auth/.well-known/jwks.json/`.
- Input events: none for core login.
- Output events: `UserCreated`, `UserUpdated`, `UserLoggedIn`, `SendOtpSmsRequested`.
- Consumers: none required for core identity.
- Dispatchers: `identity-outbox-dispatcher`.
- Notes: owns JWT private key and raw OTP verification logic.

## notification-service

- Responsibility: SMS delivery, notification jobs, reminder SMS.
- Database: notification database.
- Main endpoints: `/api/v1/notifications/health/`, `/api/v1/notifications/sms/test/`, `/api/v1/notifications/messages/`.
- Input events: `SendOtpSmsRequested`, `PaymentReminderRequested`, `SettlementConfirmationReminderRequested`, `SettlementPlanItemReminderRequested`.
- Output events: `NotificationSent`, `NotificationFailed`, `SmsSent`, `SmsFailed`.
- Consumers: notification consumer and reminder consumer.
- Dispatchers: `notification-outbox-dispatcher`.
- Notes: masks phone numbers in logs and uses circuit-breaker protection for SMS provider calls.

## group-service

- Responsibility: groups, members, invites, membership permissions.
- Database: group database.
- Main endpoints: `/api/v1/groups/`, `/api/v1/groups/{group_id}/`, `/api/v1/groups/{group_id}/members/`, `/api/v1/groups/{group_id}/invites/`, `/api/v1/groups/invites/{token}/accept/`.
- Input events: identity user events.
- Output events: `GroupCreated`, `GroupUpdated`, `GroupArchived`, `GroupInviteCreated`, `GroupInviteAccepted`, `GroupMemberJoined`, `GroupMemberRemoved`, `GroupMemberLeft`.
- Consumers: user projection consumer.
- Dispatchers: `group-outbox-dispatcher`.
- Notes: invite tokens are hashed and group membership is enforced before protected group actions.

## expense-service

- Responsibility: expense creation, equal/custom splits, tax/service-fee validation, expense events.
- Database: expense database.
- Main endpoints: `/api/v1/groups/{group_id}/expenses/`, `/api/v1/expenses/{expense_id}/`.
- Input events: identity user events and group membership events.
- Output events: `ExpenseCreated`, `ExpenseUpdated`, `ExpenseDeleted`, `ExpenseParticipantsChanged`.
- Consumers: user/group/member projection consumers.
- Dispatchers: `expense-outbox-dispatcher`.
- Notes: API payloads use `base_amount_minor`, `payer_user_id`, `split_method`, and participant share fields.

## media-service

- Responsibility: receipt upload, metadata, secure download, deletion.
- Database: media database.
- Main endpoints: `/api/v1/media/receipts/`, `/api/v1/media/files/{file_id}/`, `/api/v1/media/files/{file_id}/download/`, `/api/v1/groups/{group_id}/media/`.
- Input events: identity and group events for projections.
- Output events: `MediaUploaded`, `MediaDeleted`.
- Consumers: user/group projection consumers.
- Dispatchers: `media-outbox-dispatcher`.
- Notes: stores random filenames, file metadata, and checksums.

## settlement-service

- Responsibility: balances, debts, manual settlements, smart settlement plans, reminders.
- Database: settlement database.
- Main endpoints: `/api/v1/groups/{group_id}/balances/`, `/api/v1/groups/{group_id}/debts/`, `/api/v1/groups/{group_id}/settlements/`, `/api/v1/groups/{group_id}/settlement-plan/`, `/api/v1/settlement-plan-items/{item_id}/confirm/`.
- Input events: identity, group, and expense events.
- Output events: `SettlementCreated`, `SettlementConfirmed`, `SettlementRejected`, `SettlementCancelled`, `BalanceRecalculated`, `DebtLedgerUpdated`, `SettlementPlanGenerated`, `SettlementPlanActivated`, `SettlementPlanCompleted`, reminder request events.
- Consumers: projection and expense event consumers.
- Dispatchers: `settlement-outbox-dispatcher`.
- Notes: reminder scheduler writes reminder request events to outbox and records `ReminderDispatchLog`.
