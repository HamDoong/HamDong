# Architecture

## Overview

HamDong uses a microservice backend behind an Nginx API Gateway. Each service owns a bounded business capability and stores its own data. Services exchange events over RabbitMQ for cross-service projections and asynchronous side effects.

## Why Microservices?

The domain naturally separates into identity, groups, expenses, media, settlements, and notifications. Separating these responsibilities keeps each service easier to test, allows independent persistence, and supports event-driven updates without direct database coupling.

## Service Responsibilities

- identity-service: users, OTP login, JWT issuing, refresh/logout, JWKS.
- group-service: groups, members, invites, and group membership events.
- expense-service: expense validation, amount-minor split contracts, and expense events.
- media-service: receipt uploads, metadata, checksums, and file access.
- settlement-service: debts, balances, manual settlements, smart settlement plans, and reminders.
- notification-service: OTP SMS, reminder SMS, notification jobs, and provider resilience.

## API Gateway

Nginx exposes one public entry point at `http://localhost:8080`. It routes stable API prefixes to the owning services and keeps nested group routes for expenses, media, balances, debts, settlements, and plans away from the generic group route.

## Database-per-service

Each service uses its own database name. This avoids direct cross-service joins and supports independent ownership. Services share facts through events and local projection tables rather than direct database reads.

## PostgreSQL Role

PostgreSQL stores service-owned business data, projection tables, outbox rows, inbox rows, refresh tokens, media metadata, settlement ledgers, and notification jobs.

## Redis Role

Redis supports OTP expiration, OTP cooldown/rate-limit data, and short-lived runtime state where configured.

## RabbitMQ Role

RabbitMQ carries integration events between services. It decouples request handling from projection updates, notification delivery, settlement updates, and reminders.

## Async Communication

Producers persist events to an outbox table. Dispatchers publish events to RabbitMQ. Consumers validate envelopes and update local projections or jobs. This gives retryable, idempotent communication.

## JWT RS256 Authentication

identity-service owns the private key and signs tokens with RS256. Protected services verify tokens with a public key or JWKS and validate issuer, audience, type, expiration, issued-at, subject, and JWT ID.

## Outbox / Inbox Reliability

The outbox pattern prevents losing events when a business transaction succeeds. The inbox pattern prevents duplicate event side effects. Together they support safe retries and service restarts.

## Circuit Breaker

notification-service uses a circuit breaker around the SMS provider so repeated external failures do not block or destabilize the service.

## Future Improvements

Future work can add wallet accounting, payment gateway integration, bank callbacks, OCR receipt reading, object storage, metrics dashboards, orchestration, and client applications.
