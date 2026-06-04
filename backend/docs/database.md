# Database

## Database-per-service Approach

Each microservice owns its schema and should not read or write another service database directly. Cross-service state is shared through events and projection tables.

## identity Database

Stores users, OTP metadata where applicable, refresh token hashes, and identity outbox rows.

## group Database

Stores groups, members, invites, user projections, group outbox rows, and inbox rows.

## expense Database

Stores expenses, participants, user/group/member projections, expense outbox rows, and inbox rows.

## media Database

Stores media file metadata, access records, projections, media outbox rows, and inbox rows. File bytes are stored in the configured media storage path or provider.

## settlement Database

Stores projections, expense projections, debt ledger entries, balance snapshots, manual settlements, settlement plans, plan items, reminder dispatch logs, outbox rows, and inbox or processed-event rows.

## notification Database

Stores notification messages, notification jobs, templates or template metadata where configured, outbox rows, and inbox rows.

## Projection Tables

Projection tables store minimal copies of external service facts needed for local authorization and business logic. They are updated from RabbitMQ events.

## Outbox Tables

Outbox tables store durable event envelopes before publishing. Dispatchers publish pending rows and update status.

## Inbox or Processed Event Tables

Inbox or processed-event tables store consumed event IDs so duplicate deliveries do not create duplicate side effects.

## Why Direct Cross-service Database Access Is Avoided

Direct database access would couple deployments and schemas across services. Events plus projections preserve service ownership and allow retries, idempotency, and independent service evolution.
