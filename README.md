# HamDong

HamDong is a full-stack project for shared group expenses, receipt management, balances, manual settlements, smart settlement planning, and reminder-driven follow-up.

The repository contains:

- a React/Vite frontend in `FrontEnd/`
- a Django/DRF microservice backend in `backend/`
- one root-level Docker Compose file for running the whole stack
- one root-level README and one root-level `.gitignore`

## Project Description

The system supports OTP-based login, JWT-protected APIs, group membership and invite flows, expense registration with `amount_minor` contracts, media upload for receipts, debt and balance projections, smart settlement planning, and reminder events delivered through RabbitMQ.

## Architecture Overview

HamDong is built as a React frontend plus Django/DRF microservices behind a single Nginx API Gateway:

- `frontend` serves the local Vite React app.
- `api-gateway` exposes the backend through `http://localhost:8080`.
- `identity-service` handles OTP login, JWT issuance, JWKS, and user profile APIs.
- `group-service` manages groups, invites, and membership.
- `expense-service` stores expenses and publishes expense events.
- `media-service` stores receipt metadata and files.
- `settlement-service` projects balances and debts, manages manual settlements and smart settlement plans, and emits reminder events.
- `notification-service` sends OTP and reminder SMS messages and records notification jobs.
- RabbitMQ connects services asynchronously.
- Redis supports OTP and rate-limit style ephemeral data.
- PostgreSQL stores each service database independently.

## Tech Stack

- React + Vite + TypeScript
- Python 3
- Django + Django REST Framework
- PostgreSQL
- Redis
- RabbitMQ
- Nginx API Gateway
- JWT with RS256
- drf-spectacular / Swagger UI
- Docker Compose

## Final Repository Structure

```text
.
├── README.md
├── docker-compose.yml
├── .gitignore
├── .github/
│   └── workflows/
│       └── ci.yml
├── FrontEnd/
│   ├── package.json
│   ├── vite.config.ts
│   └── src/
└── backend/
    ├── .env.example
    ├── api-gateway/
    ├── api-tests/
    │   ├── hamdong.http
    │   ├── identity.http
    │   ├── group.http
    │   ├── expense.http
    │   ├── media.http
    │   ├── settlement.http
    │   └── notification.http
    ├── docs/
    ├── infra/
    ├── scripts/
    ├── services/
    ├── shared/
    └── tests/
```

## Configuration Ownership

Keep only one copy of each project-level file:

| File | Final location | Reason |
|---|---|---|
| README | `README.md` | One complete project README for frontend + backend |
| Docker Compose | `docker-compose.yml` | One root compose file for the full stack |
| Git ignore rules | `.gitignore` | One root ignore file for the whole repository |
| Backend env template | `backend/.env.example` | Env values are backend/infrastructure-specific |
| Backend API tests | `backend/api-tests/` | API collections belong to backend |
| Backend docs | `backend/docs/` | Backend architecture and API docs belong to backend |

Do not keep duplicate copies of these files:

```text
.env.example
api-tests/
docs/
backend/README.md
backend/.gitignore
backend/docker-compose.yml
```

## How to Run Locally

From the repository root:

1. Copy the backend environment template:

```bash
cp backend/.env.example backend/.env
```

2. Start the full stack:

```bash
docker compose --env-file backend/.env -f docker-compose.yml up --build
```

3. Check status:

```bash
docker compose --env-file backend/.env -f docker-compose.yml ps
```

4. View all logs:

```bash
docker compose --env-file backend/.env -f docker-compose.yml logs -f
```

5. View one service logs:

```bash
docker compose --env-file backend/.env -f docker-compose.yml logs -f identity-service
docker compose --env-file backend/.env -f docker-compose.yml logs -f group-service
docker compose --env-file backend/.env -f docker-compose.yml logs -f expense-service
docker compose --env-file backend/.env -f docker-compose.yml logs -f media-service
docker compose --env-file backend/.env -f docker-compose.yml logs -f settlement-service
docker compose --env-file backend/.env -f docker-compose.yml logs -f notification-service
docker compose --env-file backend/.env -f docker-compose.yml logs -f frontend
```

6. Stop the stack:

```bash
docker compose --env-file backend/.env -f docker-compose.yml down
```

7. Reset local volumes when needed:

```bash
backend/scripts/reset-local.sh
```

## Environment Variables

`backend/.env.example` contains the full local backend setup template for:

- app environment
- debug mode
- Django secret key
- PostgreSQL host, port, user, password, and per-service database names
- Redis host/port
- RabbitMQ host/port/user/password
- JWT issuer, audience, and key paths
- OTP length, TTL, cooldown, and rate limits
- SMS provider settings
- outbox / inbox / retry settings
- reminder settings
- media storage settings

The root Compose file uses `backend/.env`, so always run Compose with:

```bash
docker compose --env-file backend/.env -f docker-compose.yml ...
```

## Ports

- Frontend: `http://localhost:5173`
- Gateway: `http://localhost:8080`
- Identity Swagger: `http://localhost:8001/api/docs/`
- Group Swagger: `http://localhost:8002/api/docs/`
- Expense Swagger: `http://localhost:8003/api/docs/`
- Settlement Swagger: `http://localhost:8004/api/docs/`
- Media Swagger: `http://localhost:8005/api/docs/`
- Notification Swagger: `http://localhost:8006/api/docs/`
- RabbitMQ management: `http://localhost:15672`

## API Gateway Routes

Gateway health endpoints:

- `/api/v1/auth/health/`
- `/api/v1/groups/health/`
- `/api/v1/expenses/health/`
- `/api/v1/settlements/health/`
- `/api/v1/media/health/`
- `/api/v1/notifications/health/`

Gateway service routing:

- `/api/v1/auth/` and `/api/v1/users/` → identity-service
- `/api/v1/groups/` → group-service
- `/api/v1/expenses/` → expense-service
- `/api/v1/media/` → media-service
- `/api/v1/settlements/`, `/api/v1/settlement-plans/`, `/api/v1/settlement-plan-items/` → settlement-service
- `/api/v1/notifications/` → notification-service

Nested group routes routed away from group-service:

- `/api/v1/groups/{group_id}/expenses/` → expense-service
- `/api/v1/groups/{group_id}/media/` → media-service
- `/api/v1/groups/{group_id}/balances/` → settlement-service
- `/api/v1/groups/{group_id}/debts/` → settlement-service
- `/api/v1/groups/{group_id}/settlements/` → settlement-service
- `/api/v1/groups/{group_id}/settlement-plan/` → settlement-service

## Authentication Flow

1. Client requests OTP from `POST /api/v1/auth/otp/request/`.
2. Identity service stores OTP securely and publishes an SMS request event.
3. Client verifies OTP using `POST /api/v1/auth/otp/verify/`.
4. Identity service issues RS256 JWT access and refresh tokens.
5. Verifier services validate JWT signature, issuer, audience, token type, and claims using the identity JWKS / public key.

## OTP / SMS Flow

- OTP is generated in identity-service.
- Only hashed OTP values are stored.
- Raw OTP values are not stored in the database and are not logged.
- In local `DEBUG=true` mode, `debug_otp` may appear in the response for manual demo testing.
- notification-service sends OTP SMS through the configured SMS provider and records the result in NotificationJob / delivery logs.

## Group / Invite Flow

- Ali creates a group.
- The creator becomes the initial owner/member.
- Invite links are created per group.
- A recipient previews invite metadata using the invite token.
- Accepting an invite creates membership and emits group membership events used by downstream projections.

## Expense Flow

- Expenses are created through `POST /api/v1/groups/{group_id}/expenses/`.
- Money fields use `*_minor` values.
- The API contract uses:
  - `base_amount_minor`
  - `payer_user_id`
  - `split_method`
  - `participant_user_ids`
  - `participants[].base_share_minor` for custom amount split
  - tax and service fee fields
- Expense events are emitted for settlement projections.

## Media / Receipt Flow

- Receipts are uploaded through `POST /api/v1/media/receipts/`.
- Files are validated and stored with random internal names.
- Clients fetch file metadata, download files, and list group media through gateway routes.
- Media permissions are tied to authenticated group membership.

## Settlement Flow

- settlement-service receives expense events and maintains debt and balance projections.
- Group members can read balances and debts.
- Manual settlements can be created, confirmed, rejected, or cancelled.
- settlement-service publishes settlement events and reminder-request events.

## Smart Settlement Flow

- The system reduces the debt graph into a deterministic plan.
- `POST /api/v1/groups/{group_id}/settlement-plan/generate/` generates the plan.
- `POST /api/v1/settlement-plans/{plan_id}/activate/` activates it.
- Plan items can be reported as paid, then confirmed or rejected.
- The algorithm itself is intentionally unchanged from earlier fix packs.

## Reminder Flow

- settlement-service decides when reminders are needed.
- It stores reminder dispatch decisions and emits reminder request events through the outbox.
- notification-service consumes those events, deduplicates them, creates NotificationJob rows, renders SMS templates, and sends via the existing SMS provider with circuit breaker protection.

## Event-driven Architecture

- Outgoing business events use a standard envelope with:
  - `event_id`
  - `event_type`
  - `event_version`
  - `occurred_at`
  - `source_service`
  - `correlation_id`
  - `causation_id`
  - `routing_key`
  - `data`
- Producer services use `OutboxMessage`.
- Consumer services use `InboxMessage` or `ProcessedEvent` for idempotency.
- Retry / failed-message handling is configured through environment variables and queue policy.

## Testing

Run service tests inside the running stack:

```bash
docker compose --env-file backend/.env -f docker-compose.yml exec identity-service pytest
docker compose --env-file backend/.env -f docker-compose.yml exec group-service pytest
docker compose --env-file backend/.env -f docker-compose.yml exec expense-service pytest
docker compose --env-file backend/.env -f docker-compose.yml exec media-service pytest
docker compose --env-file backend/.env -f docker-compose.yml exec settlement-service pytest
docker compose --env-file backend/.env -f docker-compose.yml exec notification-service pytest
```

Run the gateway smoke test:

```bash
BASE_URL=http://localhost:8080 backend/scripts/smoke-test.sh
```

Run REST Client collections in VS Code:

- `backend/api-tests/identity.http`
- `backend/api-tests/group.http`
- `backend/api-tests/expense.http`
- `backend/api-tests/media.http`
- `backend/api-tests/settlement.http`
- `backend/api-tests/notification.http`
- `backend/api-tests/hamdong.http`

## API Documentation

Swagger / OpenAPI URLs:

- `http://localhost:8001/api/docs/` and `http://localhost:8001/api/schema/`
- `http://localhost:8002/api/docs/` and `http://localhost:8002/api/schema/`
- `http://localhost:8003/api/docs/` and `http://localhost:8003/api/schema/`
- `http://localhost:8004/api/docs/` and `http://localhost:8004/api/schema/`
- `http://localhost:8005/api/docs/` and `http://localhost:8005/api/schema/`
- `http://localhost:8006/api/docs/` and `http://localhost:8006/api/schema/`

## Demo Scenario

The presentation-ready walkthrough is documented in `backend/docs/demo-scenario.md` and encoded as runnable requests in `backend/api-tests/hamdong.http`.

## Troubleshooting

See `backend/docs/troubleshooting.md` for startup, gateway, JWKS, event consumer, RabbitMQ, SMS, and media issues.

## Future Improvements

- production-grade secrets management
- stronger rate limiting and audit dashboards
- richer admin tooling and observability
- formal contract tests against live containers
- async worker monitoring and DLQ dashboards
