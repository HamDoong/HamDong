# Database

## Overview

HamDong uses one PostgreSQL database per service. This keeps schemas isolated and forces all cross-service synchronization through APIs or events instead of direct table reads.

## Databases

- `identity_db`
- `group_db`
- `expense_db`
- `media_db`
- `settlement_db`
- `notification_db`

## Why One Database Per Service?

- bounded contexts keep ownership clear
- migrations stay local to each service
- accidental cross-service coupling is reduced
- event projections become explicit
- service failure domains are cleaner

## Main Data by Service

### identity-service
- user records
- refresh tokens
- OTP state / audit metadata
- outbox messages

### group-service
- groups
- members
- invite records
- user projections
- outbox / inbox

### expense-service
- expenses
- expense participants
- user/group/member projections
- outbox / inbox

### media-service
- media file metadata
- user/group projections
- outbox / inbox

### settlement-service
- user/group/member/expense projections
- debt ledger entries
- group balance snapshots
- manual settlements
- settlement plans and items
- reminder dispatch logs
- outbox / inbox / processed-event compatibility

### notification-service
- notification jobs
- delivery/provider logs
- inbox / outbox

## Data Consistency

HamDong uses eventual consistency for projections:

- source services own their write models
- downstream services build read/write projections from RabbitMQ events
- retry and duplicate handling are explicit through outbox/inbox tables

## Notes for Local Delivery

The local stack uses a shared PostgreSQL container with separate logical databases and persistent Docker volumes.
