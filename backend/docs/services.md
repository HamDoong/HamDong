# Services Reference

This page summarizes responsibilities, endpoints and event interactions for each service.

identity-service
- Responsibility: OTP auth, JWT issuance, JWKS, user projection events
- Database: `identity_db`
- Main endpoints: `POST /api/v1/auth/otp/request/`, `POST /api/v1/auth/otp/verify/`, `POST /api/v1/auth/token/refresh/`, `GET /.well-known/jwks.json`
- Input events: none (source of truth for users)
- Output events: `user.created`, `user.updated`, `otp.requested`
- Consumers: none
- Dispatchers: none

notification-service
- Responsibility: create `NotificationJob`s and send SMS/notifications
- Database: `notification_db`
- Main endpoints: `POST /api/v1/notifications/sms/test/`, `GET /api/v1/notifications/messages/`, `GET /api/v1/notifications/health/`
- Input events: `otp.requested`, `settlement.reminder.requested`, other notification-related events
- Output events: `notification.sent`, `notification.failed`
- Consumers: reminder consumer, OTP consumer
- Dispatchers: provider retry logic + circuit breaker

group-service
- Responsibility: groups, invites, membership management
- Database: `group_db`
- Main endpoints: `POST /api/v1/groups/`, `POST /api/v1/groups/{group_id}/invites/`, `POST /api/v1/groups/invites/{token}/accept/`, member management endpoints
- Input events: `user.created|updated` (identity projection)
- Output events: `group.created`, `group.member.added`, `group.member.removed`
- Consumers: identity events
- Dispatchers: invite cleanup jobs (management)

expense-service
- Responsibility: create and manage expenses, publish expense events
- Database: `expense_db`
- Main endpoints: `POST /api/v1/groups/{group_id}/expenses/`, `GET /api/v1/groups/{group_id}/expenses/list/`, expense detail endpoints
- Input events: `user.updated`, `group.member.added/removed`
- Output events: `expense.created`, `expense.updated`, `expense.deleted`
- Consumers: identity/group events for projection
- Dispatchers: none (publishes expense events via outbox if configured)

media-service
- Responsibility: receipt upload, secure download, media metadata
- Database: `media_db`
- Main endpoints: `POST /api/v1/media/receipts/`, media detail/download endpoints, `GET /api/v1/media/health/`
- Input events: `user.updated`, `group.member.added/removed`
- Output events: `media.uploaded`, `media.deleted`
- Consumers: identity/group events
- Dispatchers: media cleanup jobs

settlement-service
- Responsibility: debt ledger, generate/activate settlement plans, reminders, outbox/inbox
- Database: `settlement_db`
- Main endpoints: `POST /api/v1/groups/{group_id}/settlement-plan/generate/`, `POST /api/v1/settlement-plans/{plan_id}/activate/`, plan item and settlement endpoints, `GET /api/v1/settlements/health/`
- Input events: `expense.created|updated|deleted`, `user.updated`, `group.member.added/removed`
- Output events: `settlement.plan.generated`, `settlement.reminder.requested`, `settlement.plan.activated`, settlement lifecycle events
- Consumers: expense events and identity/group events
- Dispatchers: outbox dispatcher, reminder scheduler
