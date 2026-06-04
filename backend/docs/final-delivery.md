# Final Delivery

## Run Project

```bash
cp .env.example .env
cp Backend/.env.example Backend/.env
docker compose -f Backend/docker-compose.yml up --build
```

## Stop Project

```bash
docker compose -f Backend/docker-compose.yml down
```

## View Logs

```bash
docker compose -f Backend/docker-compose.yml logs -f
docker compose -f Backend/docker-compose.yml logs -f identity-service
docker compose -f Backend/docker-compose.yml logs -f settlement-service
```

## Run Smoke Test

```bash
BASE_URL=http://localhost:8080 Backend/scripts/smoke-test.sh
```

## Run Service Tests

```bash
docker compose -f Backend/docker-compose.yml exec identity-service pytest
docker compose -f Backend/docker-compose.yml exec group-service pytest
docker compose -f Backend/docker-compose.yml exec expense-service pytest
docker compose -f Backend/docker-compose.yml exec media-service pytest
docker compose -f Backend/docker-compose.yml exec settlement-service pytest
docker compose -f Backend/docker-compose.yml exec notification-service pytest
```

## Swagger URLs

- `http://localhost:8001/api/docs/`
- `http://localhost:8002/api/docs/`
- `http://localhost:8003/api/docs/`
- `http://localhost:8004/api/docs/`
- `http://localhost:8005/api/docs/`
- `http://localhost:8006/api/docs/`

Schemas are available at `/api/schema/` on the same service ports.

## REST Client Demo Flow

Use `api-tests/hamdong.http` for the full Ali, Sara, and Reza scenario.

## CI Behavior

The GitHub Actions workflow checks out the repository, prepares safe environment files, validates Docker Compose configuration, and builds Backend services.

## Known Limitations

Live Docker Compose startup, live Swagger access, gateway smoke testing, and containerized service tests require a local Docker environment.

## Future Improvements

Future improvements can include wallet accounting, payment gateway integration, bank callback handling, online payments, OCR receipt reading, MinIO/S3 production media storage, Grafana/Prometheus monitoring, Kubernetes deployment, and frontend or mobile integration.
