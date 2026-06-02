# Database

Each service owns its own PostgreSQL database. This isolates schemas and prevents cross-service coupling.

Key points
- identity_db: users, refresh tokens, OTP audit logs
- group_db: groups, invites, memberships
- expense_db: expenses, participants
- media_db: media files metadata
- settlement_db: debts, settlement plans, plan items, outbox/inbox
- notification_db: notification jobs, provider logs

Design rationale
- Service-per-database promotes autonomy, easier migrations, and clearer ownership.
