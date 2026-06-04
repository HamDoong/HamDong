# Testing

## Start Services

```bash
docker compose -f backend/docker-compose.yml up --build
```

## Run Service Tests

```bash
docker compose -f backend/docker-compose.yml exec identity-service pytest
docker compose -f backend/docker-compose.yml exec group-service pytest
docker compose -f backend/docker-compose.yml exec expense-service pytest
docker compose -f backend/docker-compose.yml exec media-service pytest
docker compose -f backend/docker-compose.yml exec settlement-service pytest
docker compose -f backend/docker-compose.yml exec notification-service pytest
```

## Run Smoke Test

```bash
BASE_URL=http://localhost:8080 backend/scripts/smoke-test.sh
```

The script checks all gateway health endpoints and prints `All gateway health checks passed.` on success.

## Run API Tests with VS Code REST Client

Open `api-tests/hamdong.http` or `backend/api-tests/hamdong.http`.

Use local debug OTP values when `DEBUG=true`. Copy returned `debug_otp` values into the variables at the top of the file.

## Suggested Manual Order

1. Start services.
2. Run smoke test.
3. Run identity-service tests.
4. Run group-service tests.
5. Run expense-service tests.
6. Run media-service tests.
7. Run settlement-service tests.
8. Run notification-service tests.
9. Run the REST Client demo flow.

## Troubleshooting Failing Tests

Check service logs with:

```bash
docker compose -f backend/docker-compose.yml logs -f identity-service
docker compose -f backend/docker-compose.yml logs -f rabbitmq
docker compose -f backend/docker-compose.yml logs -f postgres
```

If balance tests lag, verify RabbitMQ consumers are running and wait briefly after expense creation.
