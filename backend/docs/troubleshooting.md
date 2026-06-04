# Troubleshooting

## Docker Compose does not start

- Run `docker compose -f backend/docker-compose.yml config` first.
- Check `backend/.env` exists and has valid values.
- Confirm ports `8080`, `8001-8006`, `5432`, `6379`, and `15672` are free.

## A service keeps restarting

- Inspect logs:
  ```bash
  docker compose -f backend/docker-compose.yml logs -f <service-name>
  ```
- Verify Postgres, Redis, and RabbitMQ are healthy.
- Confirm service migrations have been applied inside the container if startup depends on schema state.

## Gateway health check fails

Run:

```bash
BASE_URL=http://localhost:8080 backend/scripts/smoke-test.sh
```

If one health endpoint fails:
- inspect gateway logs
- inspect the target service logs
- verify `api-gateway/nginx.conf` matches service names from `backend/docker-compose.yml`

## JWT / JWKS errors

- confirm identity-service is up
- confirm `IDENTITY_JWKS_URL` points to the identity service
- confirm the public key path exists where configured
- verify `JWT_ISSUER` and `JWT_AUDIENCE` match across services

## OTP problems

- verify Redis is running
- check OTP TTL/cooldown values
- in local debug mode, copy `debug_otp` manually into REST Client variables
- ensure production deployments keep `DEBUG=false`

## Event / Consumer delays

- after expense creation, wait a few seconds before reading balances or debts
- inspect outbox dispatcher logs
- inspect settlement and notification consumer logs
- verify RabbitMQ connectivity and queue bindings

## Media upload issues

- confirm the file is below `MEDIA_MAX_FILE_SIZE_BYTES`
- confirm allowed content type / validation rules
- ensure the optional REST Client fixture file exists before testing upload

## SMS / Reminder issues

- check notification-service logs
- verify `SMS_PROVIDER`, `SMS_API_KEY`, and `SMS_SENDER`
- inspect `NotificationJob` status and last error fields
- verify reminder thresholds and scheduler settings in `.env`

## Local reset

Use the reset script if you intentionally want to destroy local volumes:

```bash
backend/scripts/reset-local.sh
```
