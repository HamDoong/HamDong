# HamDong Project

Project Title
- HamDong — Collaborative group expense and settlement microservices.

Project Description
- HamDong implements group expense tracking, receipt/media uploads, smart settlement planning and SMS reminders using a small set of focused microservices.

Architecture Overview
- Microservices: identity, group, expense, media, settlement, notification. Event-driven integration via RabbitMQ, API gateway via Nginx, per-service PostgreSQL databases.

Services
- identity-service — authentication and user projection
- group-service — groups, invites, members
- expense-service — expense lifecycle and events
- media-service — receipt uploads and media storage
- settlement-service — debt ledger, settlement plans, outbox and reminders
- notification-service — SMS and notification jobs

Tech Stack
- Python, Django, Django REST Framework
- PostgreSQL, Redis
- RabbitMQ
- Docker Compose
- drf-spectacular (OpenAPI/Swagger)

Folder Structure
- backend/: all service source code and compose files
- frontend/: optional frontend assets
- docs/: architecture and how-to guides
- api-tests/: VS Code REST Client requests
- scripts/: helper and demo scripts

How to Run Locally
1. Copy and edit `.env.example` to `.env` with secrets and keys.
2. Build and start services:

    make build
    make up

3. Apply migrations:

    make migrate

4. Run tests:

    make test

Environment Variables
- See `.env.example` for required variables (Postgres, Redis, RabbitMQ, JWT, OTP, SMS, event/outbox settings).

Ports
- Nginx API Gateway: `8080`
- Identity service: `8000` (internal)
- RabbitMQ management: `15672`

API Gateway Routes
- `/api/v1/auth/` — identity endpoints (OTP, JWT, JWKS)
- `/api/v1/groups/` — group endpoints
- `/api/v1/expenses/` — expense endpoints
- `/api/v1/media/` — media endpoints
- `/api/v1/settlements/` — settlement endpoints
- `/api/v1/notifications/` — notification endpoints

Database Design Summary
- Each service owns its database and projections to avoid cross-service coupling. See `docs/database.md` for per-service tables.

Event-driven Architecture
- Services publish events to RabbitMQ and consume where needed. Outbox/Inbox patterns ensure reliable delivery and idempotency.

Authentication Flow
- OTP login: request OTP, verify OTP, receive JWT access + refresh tokens. JWT signed with RS256; services validate using JWKS from `identity-service`.

OTP/SMS Flow
- identity-service emits OTP events; notification-service creates `NotificationJob` and sends SMS via configured provider. Circuit breaker protects SMS provider.

Group/Invite Flow
- Owners create invites; invite tokens are one-time and raw tokens are not stored in DB (only hashes).

Expense Flow
- Expenses are created with `amount_minor` and participants list; events published to drive settlements.

Media/Receipt Flow
- Receipts are uploaded, validated, and stored (local in dev). Filenames randomized and checksums recorded.

Settlement Flow
- Settlement-service consumes expense events, calculates balances, and can generate a smart settlement plan.

Smart Settlement Flow
- Plan minimizes transactions by matching creditors and debtors and emits plan events.

Reminder Flow
- Reminder scheduler creates reminder events which are consumed by notification-service to send SMS reminders.

Testing
- See `docs/testing.md`. Use `make -C backend test` for all service tests and per-service `make -C backend test-<service>` targets.

API Documentation
- Each service exposes OpenAPI at `/api/schema/` and interactive docs at `/api/docs/`.

Demo Scenario
- See `docs/demo-scenario.md` and `api-tests/hamdong.http` for a runnable demo flow.

Troubleshooting
- See `docs/troubleshooting.md` for common issues and commands.

Future Improvements
- Wallet service
- Payment gateway
- Bank callback
- Online payment
- OCR receipt reading
- MinIO/S3 production storage
- Grafana/Prometheus monitoring
- Kubernetes deployment
- Mobile app / Frontend integration
