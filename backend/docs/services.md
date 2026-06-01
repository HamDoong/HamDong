# Services

Short descriptions and responsibilities for each service.

- identity-service: authentication, OTP, JWT, JWKS, publishes identity events.
- group-service: group lifecycle, invites, membership, publishes group events.
- expense-service: expense creation, participant splits, publishes expense events.
- media-service: receipt upload and media access; publishes media events.
- settlement-service: debt ledger, settlement plans, reminder scheduler, outbox.
- notification-service: consumes reminder and OTP events, creates NotificationJob, sends SMS.
