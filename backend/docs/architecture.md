# Architecture

## Overview

HamDong is implemented as a Django-based microservice backend for group expense sharing. A single Nginx API Gateway exposes the public HTTP interface, while service-to-service data synchronization is handled with RabbitMQ events. Each service owns its own PostgreSQL schema/database and does not read another service database directly.

## Why Microservices?

Microservices were selected because HamDong has clear bounded contexts with different write models and operational concerns:

- identity-service: authentication, user identity, OTP, JWT, JWKS
- group-service: groups, membership, invite lifecycle
- expense-service: expense write model and participant shares
- media-service: receipt file validation and metadata
- settlement-service: debt and balance projections, manual settlement, smart settlement planning, reminders
- notification-service: SMS delivery and notification jobs

This separation makes the project suitable for academic defense because it demonstrates:

- independent service ownership
- service-per-database boundaries
- asynchronous projection building
- event-driven reliability patterns
- bounded-context-oriented API design

## Services

- **identity-service** issues RS256 access/refresh tokens and publishes user/OTP events.
- **group-service** manages groups, members, and invites, and publishes membership events.
- **expense-service** stores expenses and publishes expense domain events for downstream projections.
- **media-service** stores file metadata and secures media access by group membership.
- **settlement-service** consumes group/identity/expense events to build balances, debts, manual settlements, and smart settlement plans.
- **notification-service** sends OTP and reminder SMS messages and records delivery outcomes.

## API Gateway

Nginx is used as a thin API Gateway because it keeps the local stack simple while still demonstrating:

- path-based routing
- central entrypoint at `localhost:8080`
- service isolation behind internal hostnames
- gateway health checks
- correct forwarding of nested group routes to expense, media, and settlement services

## Databases

Each service has its own PostgreSQL database:

- `identity_db`
- `group_db`
- `expense_db`
- `media_db`
- `settlement_db`
- `notification_db`

This design avoids direct cross-service table access and forces communication through APIs or events.

## Async Communication

RabbitMQ is used for asynchronous integration because the system needs reliable delivery of business events:

- identity events project users into downstream services
- group events project memberships
- expense events update debts and balances
- settlement reminder events trigger notification jobs

RabbitMQ also supports retry and failed-message policies for long-running workflows.

## Authentication

JWT with RS256 is used because:

- the signing private key remains only in identity-service
- verifier services can validate tokens using the public key / JWKS
- verifier services do not need to share a secret signing key
- issuer, audience, token type, and expiry are verified consistently

## Outbox / Inbox

Outbox / Inbox was added to improve event-driven reliability:

- producers create `OutboxMessage` rows in the same transaction as business changes where practical
- dispatchers publish pending outbox rows to RabbitMQ
- consumers use `InboxMessage` or `ProcessedEvent` to skip duplicates
- duplicate events do not create duplicate projections, debts, or reminder jobs

## Circuit Breaker

notification-service reuses a circuit breaker around SMS provider calls to avoid endless retries against an unhealthy provider and to keep reminder delivery failures controlled.

## Future Improvements

- stronger observability around queues and DLQs
- scheduled worker supervision and metrics
- contract testing against live service containers
- automated seed/demo orchestration beyond manual REST Client execution
