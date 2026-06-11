# Troubleshooting

## Docker Compose Fails

Validate the file first:

```bash
docker compose -f docker-compose.yml config
```

Then confirm Docker is running and required ports are free.

## Gateway `502`

Check gateway plus the target service:

```bash
docker compose -f docker-compose.yml ps
docker compose -f docker-compose.yml logs -f api-gateway
docker compose -f docker-compose.yml logs -f identity-service
```

Replace `identity-service` with the service behind the failing route.

## Health Endpoint Fails

Run:

```bash
BASE_URL=http://localhost:8080 backend/scripts/smoke-test.sh
```

Then inspect the failing service log.

## RabbitMQ Not Ready

Check the broker logs and management UI:

```bash
docker compose -f docker-compose.yml logs -f rabbitmq
```

Management UI: `http://localhost:15672`

## PostgreSQL Connection Fails

Inspect PostgreSQL logs and container health:

```bash
docker compose -f docker-compose.yml logs -f postgres
docker compose -f docker-compose.yml ps postgres
```

## Redis Connection Fails

Inspect Redis logs:

```bash
docker compose -f docker-compose.yml logs -f redis
```

## Migrations Fail

Run migrations manually in the affected service:

```bash
docker compose -f docker-compose.yml exec identity-service python manage.py migrate
```

Repeat with the affected service name.

## JWT Public Key Missing

Verify the following variables in `.env`:

- `JWT_PRIVATE_KEY_PATH`
- `JWT_PUBLIC_KEY_PATH`
- `IDENTITY_PUBLIC_KEY_PATH`
- `IDENTITY_JWKS_URL`

## OTP Not Received in Fake Provider

When `DEBUG=true`, inspect the OTP request response for `debug_otp`. Also check notification-service logs to confirm the OTP event was consumed.

## Event Consumers Delayed

Async projections depend on workers such as `group-consumer`, `expense-consumer`, `settlement-consumer`, and `notification-consumer`. Inspect the relevant worker logs:

```bash
docker compose -f docker-compose.yml logs -f settlement-consumer
docker compose -f docker-compose.yml logs -f notification-consumer
```

## Balance Not Updated Yet

Expense and settlement projections are asynchronous. Wait briefly after expense creation, then retry the balance or settlement-plan request.

## Media Upload Fails

Verify that:

- the file exists
- the file size is below `MEDIA_MAX_FILE_SIZE_BYTES`
- the extension/content type is allowed
- the media volume is writable

## Swagger Not Opening

Check the direct service logs and open the direct service docs URL, for example:

```bash
docker compose -f docker-compose.yml logs -f group-service
```

Then open `http://localhost:8002/api/docs/`.
