# HamDong IAM Service

IAM (Identity and Access Management) service for the HamDong expense sharing microservice platform. This service handles authentication, authorization, and OTP-based user verification.

## Architecture

This service follows **Clean Architecture** principles with strict layer separation:

```
src/
├── domain/              # Business logic & interfaces
│   ├── entities/       # Domain entities
│   ├── interfaces/     # Repository & service interfaces
│   └── exceptions/     # Domain exceptions
├── application/        # Use cases & DTOs
│   ├── dtos/          # Data transfer objects
│   └── use_cases/     # Application use cases
├── infrastructure/     # External integrations
│   ├── database/      # PostgreSQL repositories
│   ├── redis/         # Redis implementations
│   ├── services/      # External services (SMS, etc)
│   ├── security/      # JWT, encryption
│   └── resilience/    # Rate limiting, circuit breakers
└── presentation/       # HTTP API
    ├── api/           # FastAPI routes
    └── dependencies/  # Dependency injection
```

## Current Implementation: OTP Request Feature

### Feature: POST /api/v1/auth/otp/request

Sends a one-time password (OTP) to a user's phone number for authentication.

#### Request
```json
{
  "phone_number": "09123456789"
}
```

#### Response
```json
{
  "message": "OTP sent",
  "expires_in": 120
}
```

### Rate Limiting
- **Per Phone**: 3 requests / 5 minutes
- **Per IP**: 10 requests / minute
- **OTP TTL**: 120 seconds

### OTP Flow
1. Validate phone number format
2. Check rate limits (per phone & per IP)
3. Generate 6-digit OTP
4. Hash OTP using HMAC-SHA256
5. Store hashed OTP in Redis with TTL
6. Send SMS asynchronously (non-blocking)
7. Return success response

## Technology Stack

- **Framework**: FastAPI
- **Language**: Python 3.11+
- **Databases**: PostgreSQL, Redis
- **Testing**: Pytest + pytest-asyncio
- **Containerization**: Docker, Docker Compose
- **Security**: JWT, bcrypt, HMAC-SHA256
- **SMS**: Twilio (with mock fallback)

## Setup

### Prerequisites
- Python 3.11+
- Docker & Docker Compose
- Redis
- PostgreSQL

### Local Development

1. **Clone the repository**
```bash
cd iam-service
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Setup environment**
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. **Run with Docker Compose**
```bash
docker-compose up -d
```

6. **Start development server**
```bash
uvicorn src.main:app --reload --port 8000
```

Server will be available at `http://localhost:8000`

### API Documentation
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Testing

### Run all tests
```bash
pytest
```

### Run specific test file
```bash
pytest tests/unit/application/use_cases/test_request_otp.py
```

### Run with coverage
```bash
pytest --cov=src --cov-report=html
```

### Run only unit tests
```bash
pytest tests/unit/
```

### Run only API tests
```bash
pytest tests/api/
```

### Run tests in watch mode
```bash
pytest-watch
```

## Project Structure Details

### Domain Layer (`src/domain/`)
- **Pure business logic** with no external dependencies
- Defines interfaces for repositories and services
- Custom domain exceptions
- Domain entities

### Application Layer (`src/application/`)
- **Use cases** orchestrating business logic
- **DTOs** for inter-layer communication
- No infrastructure details

### Infrastructure Layer (`src/infrastructure/`)
- **Repository implementations** for data persistence
- **Redis integration** for caching and OTP storage
- **OTP service** for generation and verification
- **SMS service** integrations
- **Rate limiting** implementation
- **Security** utilities (JWT, hashing)

### Presentation Layer (`src/presentation/`)
- **FastAPI controllers** handling HTTP requests
- **Input validation** using Pydantic
- **Dependency injection** setup
- Thin controllers (logic in use cases)

## Key Design Decisions

1. **Clean Architecture**: Strict layer separation for maintainability
2. **Repository Pattern**: Abstract data access for testability
3. **Use Cases**: Encapsulate business logic
4. **DTOs**: Clear contracts between layers
5. **Dependency Injection**: Loose coupling for testing
6. **Rate Limiting**: Redis-based for distributed systems
7. **OTP Security**: HMAC-SHA256 hashing + timing-safe verification
8. **Async/Await**: Full async support for scalability
9. **Observability**: Structured logging with request correlation IDs
10. **Error Handling**: Domain exceptions for business logic errors

## SOLID Principles

- **S**ingle Responsibility: Each class has one reason to change
- **O**pen/Closed: Open for extension, closed for modification
- **L**iskov Substitution: Implementations follow interface contracts
- **I**nterface Segregation: Small, focused interfaces
- **D**ependency Inversion: Depend on abstractions, not concrete implementations

## Security Features

- **JWT Authentication**: For stateless auth
- **Refresh Tokens**: For long-lived sessions
- **OTP Hashing**: HMAC-SHA256 with timing-safe comparison
- **Rate Limiting**: Brute-force protection
- **RBAC Ready**: Role-based access control infrastructure
- **Input Validation**: Pydantic models for request validation
- **CORS Support**: Configurable cross-origin requests

## Resilience & Observability

- **Rate Limiting**: Prevent abuse
- **Graceful Error Handling**: User-friendly error responses
- **Structured Logging**: Request ID, user ID, event tracking
- **Metrics Ready**: Prometheus-compatible metrics structure
- **Circuit Breakers**: Ready for implementation
- **Retry Logic**: Configurable for external services

## Environment Variables

See `.env.example` for all configuration options.

Key variables:
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `JWT_SECRET_KEY`: Secret for JWT signing
- `OTP_SECRET_KEY`: Secret for OTP hashing
- `SMS_PROVIDER`: SMS service provider (mock, twilio)

## Testing Strategy

### Unit Tests
- Use case logic
- OTP service operations
- Rate limiter behavior

### Integration Tests
- Repository operations
- Redis interactions
- Database transactions

### API Tests
- Endpoint responses
- Error handling
- Request validation
- Rate limit enforcement

## Deployment

### Docker
```bash
# Build image
docker build -t hamdong-iam-service:1.0.0 .

# Run container
docker run -p 8000:8000 \
  -e DATABASE_URL="postgresql://..." \
  -e REDIS_URL="redis://..." \
  hamdong-iam-service:1.0.0
```

### Docker Compose
```bash
docker-compose up -d
```

## Performance Considerations

- **Redis Caching**: For OTP and rate limit data
- **Connection Pooling**: Database connection pooling
- **Async Operations**: Non-blocking SMS sending
- **TTL Management**: Automatic OTP expiration
- **Indexing**: Optimized database queries

## Future Enhancements

- [ ] Email OTP verification
- [ ] Social login integrations
- [ ] Multi-factor authentication (MFA)
- [ ] Session management
- [ ] User profile management
- [ ] Permission system
- [ ] Audit logging
- [ ] API key management
- [ ] OAuth2 implementation
- [ ] Metrics & Observability stack

## Contributing

Please follow these guidelines:
1. Follow Clean Architecture principles
2. Write tests for all features
3. Maintain layer separation
4. Use type hints
5. Document public APIs
6. Follow SOLID principles

## License

This project is part of the HamDong expense sharing platform.
