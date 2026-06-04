# HamDong Backend

HamDong is a Django/DRF microservice backend for shared group expenses, receipt media, debt calculation, manual settlements, smart settlement plans, and reminder notifications.

## Project Description

The backend supports OTP login, RS256 JWT authentication, group invite flows, amount-minor expense contracts, receipt uploads, balance projections, settlement workflows, RabbitMQ event processing, transactional outbox dispatch, inbox idempotency, and SMS reminders.

## Architecture Overview

Clients call the Nginx API Gateway at `http://localhost:8080`. The gateway forwards requests to service-specific Django applications. Each service owns its database schema and communicates with other services through RabbitMQ events instead of direct database access.

## Services

| Service | Responsibility |
| --- | --- |
| `identity-service` | OTP login, users, JWT issuing, refresh/logout, JWKS |
| `group-service` | groups, members, invites, group projections |
| `expense-service` | expense creation, split validation, expense events |
| `media-service` | receipt upload, metadata, download, deletion |
| `settlement-service` | balances, debts, manual settlements, smart plans, reminders |
| `notification-service` | SMS delivery, OTP messages, reminder jobs |
| `api-gateway` | public routing through Nginx |
| `postgres` | service databases |
| `redis` | OTP/rate-limit/cache support |
| `rabbitmq` | async event transport |

## Tech Stack

Python, Django, Django REST Framework, PostgreSQL, Redis, RabbitMQ, Nginx, Docker Compose, PyJWT RS256, Swagger/OpenAPI, and VS Code REST Client `.http` collections.

## Folder Structure

```text
backend/
  api-gateway/
  api-tests/
  docs/
  infra/
  scripts/
  services/
  shared/
  tests/
docs/
api-tests/
.github/workflows/
```

Root-level `docs/` and `api-tests/` mirror the final delivery documentation and REST Client collections. `backend/` contains the runnable backend stack.

## How to Run Locally

Prepare environment files:

```bash
cp .env.example .env
cp backend/.env.example backend/.env
```

Start project:

```bash
docker compose -f backend/docker-compose.yml up --build
```

Stop project:

```bash
docker compose -f backend/docker-compose.yml down
```

Check status:

```bash
docker compose -f backend/docker-compose.yml ps
```

View all logs:

```bash
docker compose -f backend/docker-compose.yml logs -f
```

View one service log:

```bash
docker compose -f backend/docker-compose.yml logs -f identity-service
docker compose -f backend/docker-compose.yml logs -f group-service
docker compose -f backend/docker-compose.yml logs -f expense-service
docker compose -f backend/docker-compose.yml logs -f media-service
docker compose -f backend/docker-compose.yml logs -f settlement-service
docker compose -f backend/docker-compose.yml logs -f notification-service
```

## Environment Variables

Use `.env.example` and `backend/.env.example` as safe templates. They include app settings, database names, Redis, RabbitMQ, JWT, OTP, SMS, outbox, reminder, and media storage settings. Do not commit real secrets.

## Ports

| Component | URL |
| --- | --- |
| API Gateway | `http://localhost:8080` |
| identity-service Swagger | `http://localhost:8001/api/docs/` |
| group-service Swagger | `http://localhost:8002/api/docs/` |
| expense-service Swagger | `http://localhost:8003/api/docs/` |
| settlement-service Swagger | `http://localhost:8004/api/docs/` |
| media-service Swagger | `http://localhost:8005/api/docs/` |
| notification-service Swagger | `http://localhost:8006/api/docs/` |
| RabbitMQ management | `http://localhost:15672` |
| PostgreSQL | `localhost:5432` |
| Redis | `localhost:6379` |

## API Gateway Routes

| Prefix | Service |
| --- | --- |
| `/api/v1/auth/` | identity-service |
| `/api/v1/users/` | identity-service |
| `/api/v1/groups/` | group-service, with nested expense/media/settlement exceptions |
| `/api/v1/expenses/` | expense-service |
| `/api/v1/media/` | media-service |
| `/api/v1/settlements/` | settlement-service |
| `/api/v1/settlement-plans/` | settlement-service |
| `/api/v1/settlement-plan-items/` | settlement-service |
| `/api/v1/notifications/` | notification-service |

Nested group routes for expenses, media, balances, debts, settlements, and settlement plans are routed to their owning services before the generic group route.

## Authentication Flow

Users request an OTP, verify the OTP, receive access and refresh tokens, and use `Authorization: Bearer <access_token>` for protected endpoints. Access tokens are RS256 signed by identity-service and verified by protected services through a public key or JWKS.

## OTP/SMS Flow

identity-service hashes OTP values, stores them with expiration, and emits `SendOtpSmsRequested`. notification-service consumes the event and sends the SMS through the configured provider. Local debug responses may expose `debug_otp` only when `DEBUG=true`.

## Group/Invite Flow

A user creates a group, gets an invite token, and shares it. Other users accept the invite and become group members. Membership is projected to other services through group events.

## Expense Flow

Expenses are created under a group with `base_amount_minor`, `payer_user_id`, `split_method`, and participant fields. Expense events update settlement projections asynchronously.

## Media/Receipt Flow

Receipt files are uploaded to media-service. The service stores metadata, a randomized stored filename, checksum, and download/delete permissions.

## Settlement Flow

settlement-service consumes expense events and updates debts and balances. Users can create manual settlements, confirm or reject them, and view balance snapshots.

## Smart Settlement Flow

The smart settlement planner generates minimized payment plan items from balances. Users can activate a plan, report a payment, and receivers can confirm or reject the item.

## Reminder Flow

settlement-service schedules reminder request events for unpaid balances, pending confirmations, and plan items. notification-service consumes those events, creates `NotificationJob` records, and sends SMS reminders with circuit-breaker protection.

## Event-driven Architecture

Events use a standard envelope with `event_id`, `event_type`, `event_version`, `occurred_at`, `source_service`, `correlation_id`, `causation_id`, `routing_key`, and `data`. Producers write `OutboxMessage` rows and dispatchers publish them. Consumers record `InboxMessage` or `ProcessedEvent` rows to skip duplicates.

## Testing

Start services, then run service tests:

```bash
docker compose -f backend/docker-compose.yml exec identity-service pytest
docker compose -f backend/docker-compose.yml exec group-service pytest
docker compose -f backend/docker-compose.yml exec expense-service pytest
docker compose -f backend/docker-compose.yml exec media-service pytest
docker compose -f backend/docker-compose.yml exec settlement-service pytest
docker compose -f backend/docker-compose.yml exec notification-service pytest
```

Run the gateway smoke test:

```bash
BASE_URL=http://localhost:8080 backend/scripts/smoke-test.sh
```

## API Documentation

Open Swagger pages:

- `http://localhost:8001/api/docs/`
- `http://localhost:8002/api/docs/`
- `http://localhost:8003/api/docs/`
- `http://localhost:8004/api/docs/`
- `http://localhost:8005/api/docs/`
- `http://localhost:8006/api/docs/`

Open OpenAPI schemas at `/api/schema/` on the same ports.

## Demo Scenario

Use `api-tests/hamdong.http` or `backend/api-tests/hamdong.http` with VS Code REST Client. The scenario logs in Ali, Sara, and Reza, creates a group, accepts invites, creates a 900000 IRR equal split expense, checks balances, generates a settlement plan, reports a payment, confirms it, and checks final balances.

## Troubleshooting

See `docs/troubleshooting.md`. Common first checks are service logs, gateway health endpoints, RabbitMQ readiness, PostgreSQL readiness, Redis availability, migrations, JWT public key path, and event consumer delays.

## Future Improvements

Future work can add a wallet service, payment gateway, bank callback, online payment, OCR receipt reading, MinIO/S3 media storage, Grafana/Prometheus monitoring, Kubernetes deployment, and frontend or mobile integration.
