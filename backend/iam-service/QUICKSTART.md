# Quick Start Guide - HamDong IAM Service

## 5-Minute Setup

### Prerequisites
- Docker & Docker Compose installed
- Python 3.11+ (for local development)
- Git

### Option 1: Using Docker Compose (Recommended)

```bash
# Navigate to iam-service directory
cd iam-service

# Start all services (PostgreSQL, Redis, IAM Service)
docker-compose up -d

# Check if service is running
curl http://localhost:8000/health

# View API documentation
# Open in browser: http://localhost:8000/docs
```

### Option 2: Local Python Development

```bash
# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env

# Start Redis (requires Redis installed)
# On macOS: brew services start redis
# On Ubuntu: sudo systemctl start redis-server
# Or use Docker: docker run -d -p 6379:6379 redis:7-alpine

# Start the server
make dev

# Or manually:
uvicorn src.main:app --reload --port 8000
```

## Testing OTP Endpoint

### Using curl

```bash
# Request OTP
curl -X POST http://localhost:8000/api/v1/auth/otp/request \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "09123456789"}'

# Response (mock):
# {"message": "OTP sent", "expires_in": 120}
```

### Using Swagger UI

1. Open http://localhost:8000/docs
2. Click on "POST /api/v1/auth/otp/request"
3. Click "Try it out"
4. Enter phone number: "09123456789"
5. Click "Execute"

## Running Tests

```bash
# Install test dependencies (included in requirements.txt)
pip install -r requirements.txt

# Run all tests
pytest

# Run with coverage report
pytest --cov=src --cov-report=html
open htmlcov/index.html

# Run specific test file
pytest tests/unit/application/use_cases/test_request_otp.py -v
```

## Common Commands

```bash
# Development server with auto-reload
make dev

# Run all tests
make test

# Run tests with coverage
make test-coverage

# Format code
make format

# Start Docker services
make docker-up

# Stop Docker services
make docker-down

# View logs
make docker-logs

# See all available commands
make help
```

## Project Structure

```
src/
├── domain/           # Business logic
├── application/      # Use cases & DTOs
├── infrastructure/   # Repositories, services
├── presentation/     # API endpoints
└── main.py          # Application factory
```

## API Endpoints

### Health Check
```
GET /health
Response: {"status": "ok", "service": "HamDong IAM Service"}
```

### Request OTP
```
POST /api/v1/auth/otp/request
Request: {"phone_number": "09123456789"}
Response: {"message": "OTP sent", "expires_in": 120}
```

## Configuration

Create `.env` file based on `.env.example`:

```env
# Server
DEBUG=false
PORT=8000

# Database
DATABASE_URL=postgresql://user:pass@localhost/db

# Redis
REDIS_URL=redis://localhost:6379/0

# Security
JWT_SECRET_KEY=your-secret-key
OTP_SECRET_KEY=your-otp-secret

# SMS (use "mock" for development)
SMS_PROVIDER=mock
```

## Troubleshooting

### Port Already in Use
```bash
# Find process using port 8000
lsof -i :8000

# Kill process
kill -9 <PID>
```

### Redis Connection Error
```bash
# Check if Redis is running
redis-cli ping
# Should respond: PONG

# If not running, start it:
# Docker: docker run -d -p 6379:6379 redis:7-alpine
# or use docker-compose
```

### Module Import Errors
```bash
# Ensure you're in iam-service directory
cd iam-service

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall

# If using Docker, rebuild
docker-compose build --no-cache
docker-compose up -d
```

## Next Steps

1. **Review Architecture**: Read [README.md](README.md) for detailed architecture
2. **Understand Use Cases**: Check [src/application/use_cases/](src/application/use_cases/)
3. **Run Tests**: Execute `make test` to ensure everything works
4. **Explore API**: Open [Swagger UI](http://localhost:8000/docs)
5. **Check Examples**: Look at test files for usage examples
6. **Contributing**: Read [CONTRIBUTING.md](CONTRIBUTING.md) guidelines

## Development Tips

### Logging
Structured logs are printed to console. Add your own:
```python
import logging
logger = logging.getLogger(__name__)
logger.info("Event", extra={"request_id": "123", "user_id": "456"})
```

### Adding New Dependencies
```bash
# Add to requirements.txt
echo "new-package==1.0.0" >> requirements.txt

# Install
pip install -r requirements.txt

# Rebuild Docker if using containers
docker-compose build
```

### Creating New Endpoints
1. Create DTO in `src/application/dtos/`
2. Create use case in `src/application/use_cases/`
3. Create endpoint in `src/presentation/api/v1/`
4. Add tests in `tests/`

### Database Migrations
(PostgreSQL setup coming in next phase)

## Environment Variables Reference

| Variable | Description | Default |
|----------|-------------|---------|
| `DEBUG` | Debug mode | false |
| `PORT` | Server port | 8000 |
| `DATABASE_URL` | PostgreSQL connection | localhost |
| `REDIS_URL` | Redis connection | localhost:6379 |
| `JWT_SECRET_KEY` | JWT signing key | change-me |
| `OTP_SECRET_KEY` | OTP hashing key | change-me |
| `OTP_TTL_SECONDS` | OTP validity period | 120 |
| `SMS_PROVIDER` | SMS service | mock |

## Getting Help

- **API Docs**: http://localhost:8000/docs
- **Code Examples**: Check `tests/` directory
- **Architecture**: Read [README.md](README.md)
- **Contributing**: See [CONTRIBUTING.md](CONTRIBUTING.md)

## What's Next?

This implementation provides the foundation for:
- ✅ OTP generation and verification
- ⏳ User registration
- ⏳ JWT authentication
- ⏳ Authorization and RBAC
- ⏳ Multi-factor authentication

Each phase builds on the previous, maintaining Clean Architecture principles.

Happy coding! 🚀
