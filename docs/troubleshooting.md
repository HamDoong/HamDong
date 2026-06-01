# Troubleshooting

Common issues and checks:

- Service won't start: check `docker compose logs <service>` and `docker compose ps`.
- Migrations failing: run `make -C backend makemigrations` then `make -C backend migrate`.
- RabbitMQ connection issues: verify host/port in `.env` and that `rabbitmq` container is healthy.
- SMS delivery failures: check SMS provider config and `SMS_PROVIDER` in `.env`.
- Duplicate events: verify processed events (Inbox) table and idempotency keys.
- JWKS issues: ensure `identity-service` JWKS endpoint is reachable and `IDENTITY_JWKS_URL` is correct.

For test failures: run failing tests with increased verbosity and check service logs.
