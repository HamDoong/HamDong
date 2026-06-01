# Architecture

Why microservices were selected
- Separation of concerns: each bounded context (identity, groups, expenses, media, settlement, notification) maps to a service.
- Independent deployment and scaling for components with different load profiles (e.g., media vs. identity).
- Teams can own services and release independently.

Each service responsibility
- identity-service: authentication, OTP, token issuance, JWKS
- group-service: groups, invites, membership management
- expense-service: expense creation, splitting, publishing expense events
- media-service: receipt upload, storage metadata, signed URLs
- settlement-service: debt ledger, settlement plan generation, reminders, Outbox
- notification-service: consume events and send SMS/notifications

Why each service has its own database
- Ownership and autonomy: services control their schema and migrations without risk of interfering with others.
- Scalability: per-service databases allow independent tuning and scaling.
- Fault isolation and simpler data models per service.

Why communication is event-driven
- Loose coupling: producers don't depend on consumers being available.
- Asynchronous workflows: long-running processes (reminders, settlements) decoupled from API latency.
- Replayability and audit: events are logged and can be replayed for rebuilding projections.

Role of Nginx
- Acts as API gateway and reverse proxy for the services, centralizing routing and TLS termination in production.

Role of RabbitMQ
- Message broker for domain events, DLX/DLQ patterns, and routing keys. Ensures decoupled event distribution.

Role of Redis
- Short-lived storage for OTP verification, caching, and rate-limiting counters.

Role of PostgreSQL
- Durable relational storage per service for core domain data, projections, outbox/inbox tables, and migrations.

Role of JWT with RS256
- Access tokens signed with RS256 allow services to verify tokens using public keys (JWKS) without sharing private keys. Refresh tokens are rotated/hashed for security.

Role of Outbox/Inbox
- Outbox: ensures messages are recorded in the producer's DB transaction before publishing; prevents message loss on failure.
- Inbox (ProcessedEvent): prevents duplicate processing by tracking event ids and idempotency keys.

Role of Circuit Breaker
- Protects fragile external integrations (SMS provider). Opens on repeated failures, prevents cascading retries and gives time for recovery.
