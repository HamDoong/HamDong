# Database

## Database-per-service Approach

Each microservice owns its own schema and must not read or write another service database directly. Shared state crosses service boundaries through RabbitMQ events and local projection tables.

## identity Database

Stores users, refresh-token hashes, OTP/rate-limit metadata where persisted, identity outbox rows, and supporting auth records.

## group Database

Stores groups, members, invites, user projections, outbox rows, and inbox rows for consumed identity events.

## expense Database

Stores expenses, participants, user/group/member projections, expense outbox rows, and inbox rows for consumed identity/group events.

## media Database

Stores media metadata, ownership/group references, checksum information, media outbox rows, and inbox rows. File bytes live in the configured media storage path/volume.

## settlement Database

Stores user/group/expense projections, balance snapshots, debt ledgers, manual settlements, settlement plans, plan items, reminder state, outbox rows, and inbox or processed-event rows.

## notification Database

Stores notification messages, provider delivery logs, reminder jobs, notification outbox rows, and inbox rows for consumed identity/settlement events.

## Projection Tables

Projection tables keep only the external facts each service needs locally, such as user identity or group membership. They are rebuilt and refreshed through event consumption rather than direct SQL joins across service boundaries.

## Outbox Tables

Outbox tables persist event envelopes before publish. Dispatcher processes fetch pending rows, publish them to RabbitMQ, and mark success/failure with retry metadata.

## Inbox / Processed Event Tables

Inbox or processed-event tables store consumed event IDs plus status so duplicate deliveries can be skipped safely.

## Why Direct Cross-service Database Access Is Avoided

Direct cross-service SQL access would tightly couple schemas, deployments, rollback plans, and migrations. Events plus projections preserve service ownership and support retries, idempotency, and independent evolution.
