# Testing

API tests with VS Code REST Client:

1. Open `api-tests/hamdong.http` in VS Code.
2. Set `@baseUrl` if your gateway runs on a different port.
3. Run requests in order and replace variables as needed.

Troubleshooting:

- If tests fail due to external services, run them with mocks or use docker compose to bring up dependencies.

| قبلاً                 | از این به بعد                                                                                 |
| --------------------- | --------------------------------------------------------------------------------------------- |
| `make up`             | `docker compose -f backend/docker-compose.yml up --build`                                     |
| `make down`           | `docker compose -f backend/docker-compose.yml down`                                           |
| `make logs`           | `docker compose -f backend/docker-compose.yml logs -f`                                        |
| `make ps`             | `docker compose -f backend/docker-compose.yml ps`                                             |
| `make test`           | `docker compose -f backend/docker-compose.yml exec <service> pytest`                          |
| `make migrate`        | `docker compose -f backend/docker-compose.yml exec <service> python manage.py migrate`        |
| `make makemigrations` | `docker compose -f backend/docker-compose.yml exec <service> python manage.py makemigrations` |
