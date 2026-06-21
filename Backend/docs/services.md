# Services

## identity-service

- **Responsibility:** OTP login, current-user profile, RS256 JWT issuing, refresh/logout, JWKS.
- **Database:** identity database.
- **Main endpoints:** `/api/v1/auth/otp/request/`, `/api/v1/auth/otp/verify/`, `/api/v1/auth/token/refresh/`, `/api/v1/auth/logout/`, `/api/v1/auth/jwks/`, `/api/v1/auth/.well-known/jwks.json`, `/api/v1/users/me/`.
- **Input events:** none for the core login flow.
- **Output events:** `UserCreated`, `UserUpdated`, `UserLoggedIn`, `SendOtpEmailRequested`.
- **Consumers:** none required for core identity flows.
- **Dispatchers:** `identity-outbox-dispatcher`.
- **Important notes:** private signing key stays here only; raw OTP values are verified here and not persisted in plain text.

## notification-service

- **Responsibility:** OTP SMS delivery, reminder SMS delivery, notification jobs, provider safety controls.
- **Database:** notification database.
- **Main endpoints:** `/api/v1/notifications/health/`, `/api/v1/notifications/sms/test/`, `/api/v1/notifications/messages/`.
- **Input events:** `SendOtpEmailRequested`, `PaymentReminderRequested`, `SettlementConfirmationReminderRequested`, `SettlementPlanItemReminderRequested`.
- **Output events:** `NotificationSent`, `NotificationFailed`, `SmsSent`, `SmsFailed`.
- **Consumers:** `notification-consumer`, `notification-reminder-consumer`.
- **Dispatchers:** `notification-outbox-dispatcher`.
- **Important notes:** masks phone numbers where practical and uses retry plus circuit-breaker protection around the SMS provider.

## group-service

- **Responsibility:** groups, members, invites, membership permissions, invite preview/accept/revoke.
- **Database:** group database.
- **Main endpoints:** `/api/v1/groups/`, `/api/v1/groups/{group_id}/`, `/api/v1/groups/{group_id}/invites/`, `/api/v1/groups/invites/{token}/`, `/api/v1/groups/invites/{token}/accept/`, `/api/v1/groups/{group_id}/members/`, `/api/v1/groups/{group_id}/leave/`.
- **Input events:** identity user events.
- **Output events:** `GroupCreated`, `GroupUpdated`, `GroupArchived`, `GroupInviteCreated`, `GroupInviteAccepted`, `GroupInviteRevoked`, `GroupMemberJoined`, `GroupMemberRemoved`, `GroupMemberLeft`.
- **Consumers:** `group-consumer`.
- **Dispatchers:** `group-outbox-dispatcher`.
- **Important notes:** invite tokens are generated as raw tokens only for the response and can be stored in hashed form for persistence checks.

## expense-service

- **Responsibility:** expense creation/update/delete, equal/custom split validation, amount-minor contract enforcement.
- **Database:** expense database.
- **Main endpoints:** `/api/v1/groups/{group_id}/expenses/`, `/api/v1/expenses/{expense_id}/`.
- **Input events:** identity user events and group membership events.
- **Output events:** `ExpenseCreated`, `ExpenseUpdated`, `ExpenseDeleted`, `ExpenseParticipantsChanged`.
- **Consumers:** `expense-consumer`.
- **Dispatchers:** `expense-outbox-dispatcher`.
- **Important notes:** payloads use `base_amount_minor`, `payer_user_id`, `split_method`, `participant_user_ids`, or `participants[].base_share_minor`. Deprecated `amount`, `paid_by`, and `paidBy` fields are not part of the current contract.

## media-service

- **Responsibility:** receipt upload, metadata lookup, secure download, deletion, group-level media listing.
- **Database:** media database plus local storage path/volume for file bytes.
- **Main endpoints:** `/api/v1/media/receipts/`, `/api/v1/media/files/{file_id}/`, `/api/v1/media/files/{file_id}/download/`, `/api/v1/groups/{group_id}/media/`.
- **Input events:** identity and group events for local projections.
- **Output events:** `MediaUploaded`, `MediaDeleted`.
- **Consumers:** `media-consumer`.
- **Dispatchers:** `media-outbox-dispatcher`.
- **Important notes:** validates file size/content type/extension, stores a randomized filename, and keeps checksum metadata.

## settlement-service

- **Responsibility:** balances, debts, manual settlements, settlement plans, reminder scheduling.
- **Database:** settlement database.
- **Main endpoints:** `/api/v1/groups/{group_id}/balances/`, `/api/v1/groups/{group_id}/balances/me/`, `/api/v1/groups/{group_id}/debts/`, `/api/v1/groups/{group_id}/settlements/`, `/api/v1/groups/{group_id}/settlement-plan/generate/`, `/api/v1/groups/{group_id}/settlement-plan/`, `/api/v1/settlement-plans/{plan_id}/activate/`, `/api/v1/settlement-plan-items/{item_id}/report-paid/`.
- **Input events:** identity events, group events, expense events.
- **Output events:** `SettlementCreated`, `SettlementConfirmed`, `SettlementRejected`, `SettlementCancelled`, `BalanceRecalculated`, `DebtLedgerUpdated`, `SettlementPlanGenerated`, `SettlementPlanActivated`, `SettlementPlanCancelled`, `SettlementPlanCompleted`, reminder request events.
- **Consumers:** `settlement-consumer`.
- **Dispatchers:** `settlement-outbox-dispatcher`.
- **Important notes:** `settlement-reminder-scheduler` periodically publishes reminder requests and balance/plan updates are asynchronous after expense events.
