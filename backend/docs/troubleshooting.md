# Troubleshooting

## Docker Compose Fails

Validate the compose file:

```bash
docker compose -f backend/docker-compose.yml config
```

Check Docker is running and ports are available.

## Gateway Returns 502

Check that the target service is running:

```bash
docker compose -f backend/docker-compose.yml ps
docker compose -f backend/docker-compose.yml logs -f api-gateway
```

Then inspect the service log, for example:

```bash
docker compose -f backend/docker-compose.yml logs -f expense-service
```

## Health Endpoint Fails

Run the smoke test and inspect the failing service:

```bash
BASE_URL=http://localhost:8080 backend/scripts/smoke-test.sh
docker compose -f backend/docker-compose.yml logs -f identity-service
```

## RabbitMQ Is Not Ready

Check RabbitMQ logs and management port:

```bash
docker compose -f backend/docker-compose.yml logs -f rabbitmq
```

Open `http://localhost:15672`.

## PostgreSQL Connection Fails

Check PostgreSQL health and credentials:

```bash
docker compose -f backend/docker-compose.yml logs -f postgres
docker compose -f backend/docker-compose.yml ps postgres
```

## Redis Connection Fails

Check Redis status:

```bash
docker compose -f backend/docker-compose.yml logs -f redis
```

## Migrations Fail

Run migrations inside the affected service container:

```bash
docker compose -f backend/docker-compose.yml exec identity-service python manage.py migrate
```

Repeat with the relevant service name.

## JWT Public Key Not Found

Verify `JWT_PUBLIC_KEY_PATH`, `JWT_PRIVATE_KEY_PATH`, and `IDENTITY_JWKS_URL` in `backend/.env`.

## OTP Not Received in Fake Provider

In local debug mode, check the OTP request response for `debug_otp`. Also inspect notification-service logs.

## Event Consumers Are Delayed

Expense and settlement projections are asynchronous. Wait a few seconds and check consumer logs:

```bash
docker compose -f backend/docker-compose.yml logs -f settlement-consumer
```

## Balance Not Updated Yet

Confirm the expense event was created and consumers are running. Then rerun the balance request.

## Media Upload Fails

Verify the file exists, file size is within `MEDIA_MAX_FILE_SIZE_BYTES`, and the media volume is writable.

## Swagger Not Opening

Check service logs and open the direct service URL, for example:

```bash
docker compose -f backend/docker-compose.yml logs -f group-service
```

Then visit `http://localhost:8002/api/docs/`.
