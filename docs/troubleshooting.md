# Troubleshooting

Common issues and checks:

- Service won't start: check `docker compose logs <service>` and `docker compose ps`.
- RabbitMQ connection issues: verify host/port in `.env` and that `rabbitmq` container is healthy.
- SMS delivery failures: check SMS provider config and `SMS_PROVIDER` in `.env`.
- Duplicate events: verify processed events (Inbox) table and idempotency keys.
- JWKS issues: ensure `identity-service` JWKS endpoint is reachable and `IDENTITY_JWKS_URL` is correct.

For test failures: run failing tests with increased verbosity and check service logs.

| قبلاً                 | از این به بعد                                                                                 |
| --------------------- | --------------------------------------------------------------------------------------------- |
| `make up`             | `docker compose -f backend/docker-compose.yml up --build`                                     |
| `make down`           | `docker compose -f backend/docker-compose.yml down`                                           |
| `make logs`           | `docker compose -f backend/docker-compose.yml logs -f`                                        |
| `make ps`             | `docker compose -f backend/docker-compose.yml ps`                                             |
| `make test`           | `docker compose -f backend/docker-compose.yml exec <service> pytest`                          |
| `make migrate`        | `docker compose -f backend/docker-compose.yml exec <service> python manage.py migrate`        |
| `make makemigrations` | `docker compose -f backend/docker-compose.yml exec <service> python manage.py makemigrations` |
