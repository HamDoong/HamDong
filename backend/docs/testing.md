# Testing

## Start Services

```bash
docker compose -f docker-compose.yml up --build
```

## Validate Compose Configuration

```bash
docker compose -f docker-compose.yml config
```

## Run Service Tests

```bash
docker compose -f docker-compose.yml exec identity-service pytest
docker compose -f docker-compose.yml exec group-service pytest
docker compose -f docker-compose.yml exec expense-service pytest
docker compose -f docker-compose.yml exec media-service pytest
docker compose -f docker-compose.yml exec settlement-service pytest
docker compose -f docker-compose.yml exec notification-service pytest
```

## Run Smoke Test

```bash
BASE_URL=http://localhost:8080 backend/scripts/smoke-test.sh
```

Expected success message:

```text
All gateway health checks passed.
```

## Run API Tests with VS Code REST Client

Open `api-tests/hamdong.http`.

- Request OTP for Ali, Sara, and Reza.
- Copy `debug_otp` values when `DEBUG=true`.
- Follow the group, invite, expense, balances, settlement-plan, report-paid, confirm, and final-balance requests in order.
- Wait briefly at the noted async checkpoints so RabbitMQ consumers can update projections.

## Suggested Manual Order

1. Start the stack.
2. Validate compose configuration.
3. Run the smoke test.
4. Run service tests for the service you are changing.
5. Run the full demo flow from `api-tests/hamdong.http`.

## Troubleshooting Failing Tests

Useful logs:

```bash
docker compose -f docker-compose.yml logs -f api-gateway
docker compose -f docker-compose.yml logs -f postgres
docker compose -f docker-compose.yml logs -f rabbitmq
docker compose -f docker-compose.yml logs -f settlement-consumer
```

If balance or plan responses lag, wait briefly and verify the relevant consumer is still running.
