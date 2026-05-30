# HamDong Backend (Phase 1)

Phase 1 focuses on the infrastructure and project skeleton for a Django + DRF microservice monorepo. Business features are intentionally not implemented yet.

## Project Overview
- Microservice architecture with separate Django services
- Nginx API gateway routing
- PostgreSQL (single container, multiple databases)
- Redis and RabbitMQ (management enabled)
- Swagger/OpenAPI via drf-spectacular
- Ruff and Black for linting/formatting
- debugpy and VS Code launch configs

## Architecture Overview
Each service is isolated with its own Django settings, URLs, Dockerfile, requirements, and database. Common contracts/events/libs live in the shared folder for future reuse.

## Services
- identity-service
- group-service
- expense-service
- settlement-service
- media-service
- notification-service

## Infrastructure
- PostgreSQL (multiple databases)
- Redis
- RabbitMQ (management UI)
- Nginx API gateway

## Setup
1. Copy environment variables:
   ```bash
   cp .env.example .env
   ```
2. Build and start:
   ```bash
   docker compose up --build
   ```

## Health Endpoints (via Nginx)
- http://localhost:8080/api/v1/auth/health/
- http://localhost:8080/api/v1/groups/health/
- http://localhost:8080/api/v1/expenses/health/
- http://localhost:8080/api/v1/settlements/health/
- http://localhost:8080/api/v1/media/health/
- http://localhost:8080/api/v1/notifications/health/

## Swagger/OpenAPI
Each service exposes:
- `/api/schema/`
- `/api/docs/`

Examples (service direct ports):
- http://localhost:8001/api/docs/
- http://localhost:8002/api/docs/

## RabbitMQ Management
- http://localhost:15672

## Makefile Commands
- `make build`
- `make up`
- `make down`
- `make logs`
- `make ps`
- `make migrate`
- `make makemigrations`
- `make test`
- `make lint`
- `make format`

## Phase 1 Non-Goals (Intentionally Not Implemented)
- Registration, OTP, or real JWT auth
- SMS integration
- Domain models for users/groups/expenses/settlements
- Receipt upload or media processing
- Real RabbitMQ publishers/consumers
- Real Celery tasks
- Circuit breaker logic
- Wallet or payment gateway
- Frontend or observability stack

## Final Verification Checklist
- `docker compose up --build` works.
- All services are running.
- All health endpoints return HTTP 200 through Nginx.
- PostgreSQL contains all six service databases.
- RabbitMQ Management opens on http://localhost:15672.
- Swagger docs are available.
- Clean Architecture folders exist in every service.
- No business logic was implemented.

## Compatibility Note
Django 6 is not yet a stable release for most environments at the time of this phase. This setup uses Django 5.1 (compatible, stable) and documents the target upgrade later.
