# HamDong Backend

## Project Title

HamDong Backend

## Project Description

HamDong is a Django/DRF microservice backend for shared group expenses, receipt media, debt tracking, manual settlements, smart settlement plans, and reminder notifications. The stack is designed for local development with Docker Compose and for presentation/demo flows through the API gateway.

## Architecture Overview

Clients call the Nginx API Gateway at `http://localhost:8080`. The gateway forwards requests to service-specific Django applications. Each service owns its own database schema and shares cross-service facts through RabbitMQ events plus local projection tables instead of direct database access.

## Services

| Service | Responsibility |
| --- | --- |
| `identity-service` | OTP login, RS256 JWT issuing, refresh/logout, JWKS, current-user profile |
| `group-service` | groups, members, invite lifecycle, membership projection events |
| `expense-service` | expense validation, equal/custom split contracts, expense events |
| `media-service` | receipt upload, metadata, checksum tracking, secure download/delete |
| `settlement-service` | balances, debts, manual settlements, smart plans, reminders |
| `notification-service` | OTP/reminder SMS delivery, notification jobs, provider circuit breaker |
| `api-gateway` | single public entry point through Nginx |
| `postgres` | per-service PostgreSQL databases |
| `redis` | OTP cooldown/rate-limit/cache support |
| `rabbitmq` | asynchronous event transport |

## Tech Stack

Python 3.12, Django, Django REST Framework, drf-spectacular/Swagger, PostgreSQL, Redis, RabbitMQ, Nginx, Docker Compose, PyJWT RS256, and VS Code REST Client `.http` collections.

## Folder Structure

```text
.
├── README.md
├── .env.example
├── .github/workflows/ci.yml
├── api-tests/
├── docs/
└── backend/
    ├── README.md
    ├── .env.example
    ├── docker-compose.yml
    ├── api-gateway/
    ├── api-tests/
    ├── docs/
    ├── infra/
    ├── scripts/
    ├── services/
    ├── shared/
    └── tests/
```

Root `docs/` and `api-tests/` are final-delivery copies. `backend/` contains the runnable stack, worker commands, contracts, scripts, and service code.

## How to Run Locally

Prepare environment files:

```bash
cp .env.example .env
cp backend/.env.example backend/.env
```

Start the stack:

```bash
docker compose -f backend/docker-compose.yml up --build
```

Stop the stack:

```bash
docker compose -f backend/docker-compose.yml down
```

Check container status:

```bash
docker compose -f backend/docker-compose.yml ps
```

View logs:

```bash
docker compose -f backend/docker-compose.yml logs -f
```

View a single service log:

```bash
docker compose -f backend/docker-compose.yml logs -f identity-service
docker compose -f backend/docker-compose.yml logs -f group-service
docker compose -f backend/docker-compose.yml logs -f expense-service
docker compose -f backend/docker-compose.yml logs -f media-service
docker compose -f backend/docker-compose.yml logs -f settlement-service
docker compose -f backend/docker-compose.yml logs -f notification-service
```

## Environment Variables

Use `.env.example` and `backend/.env.example` as safe templates. They contain placeholders for app mode, secrets, PostgreSQL, Redis, RabbitMQ, JWT, OTP, SMS, outbox/retry settings, reminder settings, and media storage configuration. Do not commit real secrets, real SMS credentials, or real private-key material.

## Ports

| Component | URL / Port |
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

| Prefix | Owner |
| --- | --- |
| `/api/v1/auth/` | identity-service |
| `/api/v1/users/` | identity-service |
| `/api/v1/groups/` | group-service |
| `/api/v1/groups/{group_id}/expenses/` | expense-service |
| `/api/v1/groups/{group_id}/media/` | media-service |
| `/api/v1/groups/{group_id}/balances/` | settlement-service |
| `/api/v1/groups/{group_id}/debts/` | settlement-service |
| `/api/v1/groups/{group_id}/settlements/` | settlement-service |
| `/api/v1/groups/{group_id}/settlement-plan/` | settlement-service |
| `/api/v1/expenses/` | expense-service |
| `/api/v1/media/` | media-service |
| `/api/v1/settlements/` | settlement-service |
| `/api/v1/settlement-plans/` | settlement-service |
| `/api/v1/settlement-plan-items/` | settlement-service |
| `/api/v1/notifications/` | notification-service |

Nested group routes are matched before the generic `/api/v1/groups/` gateway location so requests reach the correct service.

## Authentication Flow

1. Client requests an OTP from identity-service.
2. Client verifies the OTP.
3. identity-service returns RS256-signed `access_token` and `refresh_token`.
4. Protected endpoints use `Authorization: Bearer <access_token>`.
5. Verifier services use the public key or JWKS and validate issuer, audience, token type, expiration, issued-at, subject, and JWT ID.

## OTP/SMS Flow

identity-service hashes the OTP, stores TTL/cooldown state, and writes `SendOtpSmsRequested` to the outbox. `identity-outbox-dispatcher` publishes the event to `hamdong.identity`. notification-service consumes the event, records idempotency, and sends an SMS through the configured provider. In local debug mode, the OTP request response may include `debug_otp`.

## Group/Invite Flow

Ali creates a group, creates an invite, and shares the invite token or URL. Sara and Reza accept the invite with their own tokens. group-service emits membership events so expense-service, media-service, and settlement-service can update their local projections.

## Expense Flow

Expenses are created under `/api/v1/groups/{group_id}/expenses/`. The current contract uses `base_amount_minor`, `payer_user_id`, `split_method`, `participant_user_ids`, or `participants[].base_share_minor`. expense-service validates the payload, stores the expense, and emits expense events.

## Media/Receipt Flow

media-service accepts receipt uploads at `/api/v1/media/receipts/`. It validates file type and size, stores a randomized filename, records checksum/metadata, and exposes detail, list, download, and delete endpoints with auth checks.

## Settlement Flow

settlement-service maintains balances and debts from group membership plus expense events. Users can list balances, view debts, create manual settlements, confirm or reject them, and query the latest settlement plan for a group.

## Smart Settlement Flow

The smart planner minimizes the number of transfers needed to settle current balances. It generates plan items, activates the plan, allows the payer to report a payment, and allows the receiver to confirm or reject the report.

## Reminder Flow

settlement-service can schedule reminder request events for unpaid balances, pending confirmations, and active settlement plan items. notification-service consumes those reminder events, creates notification jobs, renders SMS content, and sends messages with retry and circuit-breaker protections.

## Event-driven Architecture

The stack uses RabbitMQ plus outbox/inbox patterns. Producers write domain data and an `OutboxMessage` in the same transaction. Dispatchers publish pending rows. Consumers validate the event envelope, record `InboxMessage` or processed-event state, skip duplicate `event_id` values, and update local projections.

## Testing

Start the stack:

```bash
docker compose -f backend/docker-compose.yml up --build
```

Run the smoke test:

```bash
BASE_URL=http://localhost:8080 backend/scripts/smoke-test.sh
```

Run service test suites where practical:

```bash
docker compose -f backend/docker-compose.yml exec identity-service pytest
docker compose -f backend/docker-compose.yml exec group-service pytest
docker compose -f backend/docker-compose.yml exec expense-service pytest
docker compose -f backend/docker-compose.yml exec media-service pytest
docker compose -f backend/docker-compose.yml exec settlement-service pytest
docker compose -f backend/docker-compose.yml exec notification-service pytest
```

Run the end-to-end demo with VS Code REST Client using `api-tests/hamdong.http`.

## API Documentation

Swagger UI:

- `http://localhost:8001/api/docs/`
- `http://localhost:8002/api/docs/`
- `http://localhost:8003/api/docs/`
- `http://localhost:8004/api/docs/`
- `http://localhost:8005/api/docs/`
- `http://localhost:8006/api/docs/`

OpenAPI schema endpoints:

- `http://localhost:8001/api/schema/`
- `http://localhost:8002/api/schema/`
- `http://localhost:8003/api/schema/`
- `http://localhost:8004/api/schema/`
- `http://localhost:8005/api/schema/`
- `http://localhost:8006/api/schema/`

## Demo Scenario

Use `api-tests/hamdong.http` for the presentation flow with Ali, Sara, and Reza in group `شام جمعه`. The file walks through OTP login, group creation, invite acceptance, a `900000 IRR` equal-split expense, balance checks, settlement-plan generation, plan activation, payment reporting, confirmation, and final balances.

## Troubleshooting

See `docs/troubleshooting.md` for Docker Compose failures, gateway `502`, health endpoint errors, RabbitMQ readiness, PostgreSQL/Redis issues, migration failures, JWT key problems, debug OTP handling, async projection delays, media upload failures, and Swagger issues.

## Future Improvements

Practical next steps include stronger integration-test coverage, trace/correlation dashboards, better backup/restore runbooks, production secret-store wiring, stricter gateway rate limiting, and richer operational health dashboards.
