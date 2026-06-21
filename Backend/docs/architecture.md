# Architecture

## Why Microservices Were Selected

HamDong separates identity, groups, expenses, media, settlements, and notifications because each area owns a distinct data model, lifecycle, and scaling pattern. OTP delivery and reminder sending are asynchronous. Settlement projections depend on expense events. Media storage has different operational concerns than authentication. Splitting these responsibilities keeps ownership clear and avoids one large Django app with cross-cutting migrations and tight coupling.

## Service Responsibilities

- **identity-service**: OTP login, JWT issuing, refresh/logout, JWKS, current-user profile.
- **group-service**: groups, members, invites, membership events.
- **expense-service**: expense validation, equal/custom split contracts, expense events.
- **media-service**: receipt uploads, metadata, checksums, download/delete rules.
- **settlement-service**: balances, debts, manual settlements, smart plans, reminders.
- **notification-service**: OTP/reminder SMS delivery and provider resilience.

## Database-per-service

Each service owns its own PostgreSQL schema and must not read another service database directly. Cross-service facts are replicated through events and local projection tables. This keeps schema changes local, supports independent migrations, and avoids hidden cross-service joins.

## Nginx API Gateway

Nginx exposes one public entry point at `http://localhost:8080`. It forwards stable public prefixes to the owning service and gives nested group routes for expenses, media, balances, debts, settlements, and settlement plans higher priority than the generic groups route.

## RabbitMQ

RabbitMQ carries integration events between services. Producers publish through service-specific exchanges such as `hamdong.identity`, `hamdong.group`, `hamdong.expense`, and `hamdong.settlement`. Consumers bind their own queues and update local projections, notification jobs, or reminder workflows.

## Redis

Redis supports OTP TTL state, resend cooldowns, verification throttling, and other short-lived operational state. It reduces database churn for time-sensitive OTP and rate-limit checks.

## PostgreSQL

PostgreSQL stores business entities plus reliability records such as refresh tokens, outbox rows, inbox rows, processed-event rows, balance snapshots, debt ledgers, media metadata, and notification jobs.

## JWT with RS256

identity-service owns the private signing key and issues RS256 access/refresh tokens. Protected services verify access tokens through the public key or the JWKS endpoint and validate issuer, audience, type, expiration, issued-at, subject, and JWT ID.

## Outbox / Inbox

Producers write domain state and an outbox record in the same transaction. Dedicated dispatcher processes publish pending outbox rows to RabbitMQ. Consumers store `InboxMessage` or processed-event state so duplicate deliveries do not create duplicate side effects. This gives at-least-once delivery with idempotent processing.

## Circuit Breaker

notification-service wraps SMS provider calls with a circuit breaker. Repeated provider failures do not continuously block the worker or flood a broken downstream provider. Retry settings and DLQ behavior are configured through environment variables.

## Future Improvements

Next improvements should stay operational and delivery-focused: broader integration tests, message tracing, dashboarding around queues and retries, stronger secret-store integration, and automated backup/restore validation.
