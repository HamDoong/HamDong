# Identity Service - Phase 2

## Phase 2 Overview

Identity Service is HamDong's authentication and authorization service. Phase 2 implements OTP login, RS256 JWT access and refresh tokens, current-user profile endpoints, JWKS publishing, and RabbitMQ identity events.

### What Phase 2 includes

- OTP request and verification with Redis-backed hashing, TTL, cooldown, and rate limiting
- RS256 access and refresh JWT generation and validation
- Refresh token rotation and logout revocation
- Current user profile retrieval and updates
- JWKS endpoint for downstream token validation
- Identity event publishing through RabbitMQ

### What Phase 2 intentionally excludes

- Real SMS delivery
- Notification-service consumers
- Production key material in the repository
- Social login, password login, and MFA flows beyond OTP

## Quick Start

### Generate local JWT keys

Use the management command inside the running identity-service container:

```bash
docker exec Backend-identity-service-1 python manage.py generate_keys --keys-dir=/app/keys
```

This creates `private.pem` and `public.pem` for local development only. Do not commit real production keys.

### Run migrations

```bash
cd Backend
docker compose exec identity-service python manage.py migrate
```

### Run tests

```bash
cd Backend
docker compose exec identity-service python manage.py test apps.identity.tests -v2
```

## Features

### OTP (One-Time Password) Authentication
- 6-digit OTP generation
- 120-second TTL (Time To Live)
- Rate limiting (3 requests per 10 minutes)
- 60-second resend cooldown
- 5 max verification attempts
- Secure OTP hashing using SHA256
- Debug mode support for development
- Real SMS sending is not implemented in Phase 2

### JWT Tokens
- RS256 signing algorithm
- Access tokens (900 seconds lifetime)
- Refresh tokens (604800 seconds / 7 days lifetime)
- Refresh token rotation
- Token revocation support

### User Management
- Custom User model with UUID primary key
- Phone number as unique identifier
- Display name, first name, last name fields
- Phone verification tracking
- User role support (USER, ADMIN)
- Last login tracking
- Soft delete with `deleted_at` field

### Events
- `UserOtpRequested` - Published when OTP is requested
- `UserCreated` - Published when a new user is created
- `UserLoggedIn` - Published on successful login
- `UserUpdated` - Published when user profile is updated
- RabbitMQ integration with topic exchange

## Architecture

### Clean Architecture Implementation

```
apps/identity/
├── api/              # API layer (views, serializers, permissions)
├── application/      # Use cases and services
├── domain/           # Models, events, rules, value objects
├── infrastructure/   # Repositories, key loader, Redis, RabbitMQ
└── tests/            # Comprehensive test suite
```

### Key Components

**Domain Layer:**
- `models.py` - User and RefreshToken models
- `events.py` - Domain events for publishing
- `rules.py` - Business rules (phone validation, OTP validation)

**Infrastructure Layer:**
- `repositories.py` - Data access layer
- `redis_otp_store.py` - Redis OTP management with hashing
- `rabbitmq_publisher.py` - Event publishing to RabbitMQ
- `key_loader.py` - JWT key loading from filesystem

**Application Layer:**
- `token_service.py` - JWT token generation and verification
- `otp_service.py` - OTP generation and verification
- `user_service.py` - User CRUD operations
- `use_cases.py` - Business logic orchestration

**API Layer:**
- `views.py` - API endpoints
- `serializers.py` - Request/response validation
- `permissions.py` - Custom authentication permission
- `urls.py` - URL routing

## API Endpoints

### OTP Management

#### Request OTP
```
POST /api/v1/auth/otp/request/

Request:
{
  "email": "09123456789"
}

Response (200 OK):
{
  "message": "OTP has been requested successfully.",
  "expires_in": 120,
  "resend_after": 60,
  "debug_otp": "123456"  // Only in DEBUG mode with OTP_DEBUG_RETURN_CODE=true
}

Error Responses:
- 400: INVALID_EMAIL
- 429: OTP_RATE_LIMITED
- 429: OTP_IN_COOLDOWN
```

How to use it:

1. Send the request to `POST /api/v1/auth/otp/request/` with a valid email address.
2. If `DEBUG=true` and `OTP_DEBUG_RETURN_CODE=true`, use the returned `debug_otp` locally.
3. Real SMS delivery is intentionally not implemented in Phase 2.

#### Verify OTP
```
POST /api/v1/auth/otp/verify/

Request:
{
  "email": "09123456789",
  "code": "123456"
}

Response (200 OK):
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "Bearer",
  "expires_in": 900,
  "user": {
    "id": "uuid",
    "email": "09123456789",
    "art_name": null,
    "is_email_verified": true,
    "role": "USER"
  }
}

Error Responses:
- 400: INVALID_OTP
- 400: OTP_EXPIRED
- 429: OTP_MAX_ATTEMPTS_EXCEEDED
```

How to use it:

1. Send the request to `POST /api/v1/auth/otp/verify/` with the email address and 6-digit code.
2. A successful response returns an access token, refresh token, token type, expiry, and user payload.
3. The OTP is deleted from Redis after successful verification.

### Token Management

#### Refresh Token
```
POST /api/v1/auth/token/refresh/

Request:
{
  "refresh_token": "eyJ..."
}

Response (200 OK):
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "Bearer",
  "expires_in": 900
}

Error Responses:
- 401: INVALID_TOKEN
```

How to use it:

1. Keep the refresh token from OTP verification or a prior refresh response.
2. Send it to `POST /api/v1/auth/token/refresh/`.
3. The old refresh token is revoked and a new access token plus new refresh token are returned.

#### Logout
```
POST /api/v1/auth/logout/

Request:
{
  "refresh_token": "eyJ..."
}

Response (200 OK):
{
  "message": "Logged out successfully."
}

Error Responses:
- 401: INVALID_TOKEN
```

How to use it:

1. Send the refresh token to `POST /api/v1/auth/logout/`.
2. The matching refresh token is revoked.
3. Reusing a revoked refresh token after logout or rotation fails.

#### Get JWKS
```
GET /api/v1/auth/jwks/
GET /api/v1/auth/.well-known/jwks.json

Response (200 OK):
{
  "keys": [
    {
      "kty": "RSA",
      "use": "sig",
      "alg": "RS256",
      "n": "...",
      "e": "AQAB",
      "kid": "identity-service-key"
    }
  ]
}
```

The JWKS endpoint is public and returns the RSA public key material needed by other services to validate RS256 access tokens.

### User Management

#### Get Current User
```
GET /api/v1/users/me/
Authorization: Bearer <access_token>

Response (200 OK):
{
  "id": "uuid",
  "email": "09123456789",
  "art_name": "Ali Ahmadi",
  "first_name": "Ali",
  "last_name": "Ahmadi",
  "is_email_verified": true,
  "role": "USER"
}

Error Responses:
- 401: UNAUTHORIZED
- 404: USER_NOT_FOUND
```

How to use it:

1. Include the access token as `Authorization: Bearer <access_token>`.
2. The token must be a valid RS256 access token with `type=access`.
3. The endpoint reads the `sub` claim and loads the current user.

#### Update Current User
```
PATCH /api/v1/users/me/
Authorization: Bearer <access_token>

Request (any combination of):
{
  "art_name": "Ali Ahmadi",
  "first_name": "Ali",
  "last_name": "Ahmadi"
}

Response (200 OK):
{
  "id": "uuid",
  "email": "09123456789",
  "art_name": "Ali Ahmadi",
  "first_name": "Ali",
  "last_name": "Ahmadi",
  "is_email_verified": true,
  "role": "USER"
}

Error Responses:
- 401: UNAUTHORIZED
- 404: USER_NOT_FOUND
```

How to use it:

1. Include the access token as `Authorization: Bearer <access_token>`.
2. Send any combination of `art_name`, `first_name`, and `last_name`.
3. Phone number, role, `is_staff`, and `is_active` are intentionally not editable here.

## Setup and Running

### Prerequisites

- Python 3.10+
- Django 5.1+
- PostgreSQL (running in Docker)
- Redis (running in Docker)
- RabbitMQ (running in Docker)

### Generate JWT Keys

**For local development:**

```bash
docker compose exec identity-service python manage.py generate_keys --keys-dir=/app/keys
```

This will create:
- `/app/keys/private.pem` - Private key for signing tokens
- `/app/keys/public.pem` - Public key for verification

**For production:**
Use proper key management. Private keys should never be committed to version control.

### Database Migrations

```bash
docker compose exec identity-service python manage.py migrate
```

### Running the Service

```bash
docker compose up identity-service
```

The service will be available at `http://localhost:8001`
Swagger documentation at `http://localhost:8001/api/docs/`

### Running Tests

```bash
# All tests
docker compose exec identity-service pytest

# Specific test file
docker compose exec identity-service pytest apps/identity/tests/test_otp_request.py

# With coverage
docker compose exec identity-service pytest --cov=apps.identity
```

## Environment Variables

```env
# JWT Configuration
JWT_ALGORITHM=RS256
JWT_ISSUER=hamdong.identity-service
JWT_AUDIENCE=hamdong.services
JWT_ACCESS_TOKEN_LIFETIME_SECONDS=900
JWT_REFRESH_TOKEN_LIFETIME_SECONDS=604800
JWT_PRIVATE_KEY_PATH=/app/keys/private.pem
JWT_PUBLIC_KEY_PATH=/app/keys/public.pem

# OTP Configuration
OTP_LENGTH=6
OTP_TTL_SECONDS=120
OTP_RESEND_COOLDOWN_SECONDS=60
OTP_MAX_VERIFY_ATTEMPTS=5
OTP_MAX_REQUESTS_PER_WINDOW=3
OTP_RATE_LIMIT_WINDOW_SECONDS=600
OTP_DEBUG_RETURN_CODE=true  # Set to false in production

# RabbitMQ Configuration
IDENTITY_RABBITMQ_EXCHANGE=hamdong.identity

# Database
POSTGRES_DB=identity_db
POSTGRES_USER=hamdong
POSTGRES_PASSWORD=hamdong_password
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0

# RabbitMQ
RABBITMQ_HOST=rabbitmq
RABBITMQ_PORT=5672
RABBITMQ_DEFAULT_USER=hamdong
RABBITMQ_DEFAULT_PASS=hamdong_password
```

## Example Usage

### 1. Request OTP

```bash
curl -X POST http://localhost:8001/api/v1/auth/otp/request/ \
  -H "Content-Type: application/json" \
  -d '{"email": "09123456789"}'
```

Response:
```json
{
  "message": "OTP has been requested successfully.",
  "expires_in": 120,
  "resend_after": 60,
  "debug_otp": "123456"
}
```

### 2. Verify OTP and Get Tokens

```bash
curl -X POST http://localhost:8001/api/v1/auth/otp/verify/ \
  -H "Content-Type: application/json" \
  -d '{"email": "09123456789", "code": "123456"}'
```

Response:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9...",
  "token_type": "Bearer",
  "expires_in": 900,
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "09123456789",
    "art_name": null,
    "is_email_verified": true,
    "role": "USER"
  }
}
```

### 3. Get Current User

```bash
curl -X GET http://localhost:8001/api/v1/users/me/ \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9..."
```

### 4. Update User Profile

```bash
curl -X PATCH http://localhost:8001/api/v1/users/me/ \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "art_name": "Ali Ahmadi",
    "first_name": "Ali",
    "last_name": "Ahmadi"
  }'
```

### 5. Refresh Token

```bash
curl -X POST http://localhost:8001/api/v1/auth/token/refresh/ \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9..."}'
```

### 6. Logout

```bash
curl -X POST http://localhost:8001/api/v1/auth/logout/ \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9..."}'
```

### 7. Get JWKS

```bash
curl -X GET http://localhost:8001/api/v1/auth/jwks/
```

## Security Notes

### OTP Security
- OTP is never stored in plain text
- SHA256 hashing is used for OTP storage in Redis
- OTP is deleted immediately after successful verification
- Rate limiting prevents brute force attacks
- Maximum of 5 verification attempts per OTP

### Token Security
- Refresh tokens are hashed before storage in PostgreSQL
- Raw refresh token is never logged or exposed
- Refresh tokens can be revoked (logout)
- Token rotation on refresh ensures old tokens become invalid
- RS256 asymmetric signing prevents tampering

### Password-less Authentication
- No passwords stored in the system
- OTP-only authentication for Phase 2
- Phone number is the unique identifier
- Phone verification is tracked

## What's NOT Implemented in Phase 2

- Real SMS sending (Phase 3)
- Email verification
- Password-based authentication
- Social login (OAuth, Google, Facebook)
- Multi-factor authentication
- User roles management UI
- Admin panel
- User deletion (soft delete only)
- Session management for web clients

## Testing

The identity service includes comprehensive tests:

- OTP request validation and rate limiting
- OTP verification with new and existing users
- Invalid OTP handling
- Token refresh and rotation
- Token revocation on logout
- User profile updates
- Phone number validation
- Event publishing
- JWKS endpoint
- Authentication with invalid tokens

Run tests with:
```bash
docker compose exec identity-service pytest apps/identity/tests/ -v
```

## Integration with Other Services

Other services can validate access tokens by:

1. Getting the JWKS from `/api/v1/auth/jwks/`
2. Loading the public key
3. Validating tokens locally using RS256

Example (in another service):
```python
import jwt
from django.conf import settings

# Get public key from identity service JWKS
public_key = "..."  # Retrieved from JWKS endpoint

# Validate token
try:
    payload = jwt.decode(
        token,
        public_key,
        algorithms=["RS256"],
        audience="hamdong.services",
        issuer="hamdong.identity-service"
    )
    user_id = payload["sub"]
    email = payload["email"]
    role = payload["role"]
except jwt.InvalidTokenError:
    # Token is invalid
    pass
```

## Troubleshooting

### JWT Key Loading Error
If you see "Private key not found":
```bash
docker compose exec identity-service python manage.py generate_keys
```

### OTP Not Being Received
In development, OTP is returned in the response when `DEBUG=true` and `OTP_DEBUG_RETURN_CODE=true`.
Check `/api/docs/` Swagger UI for the debug_otp field.

### RabbitMQ Connection Issues
Events are published asynchronously and failures don't block the auth flow.
Check service logs: `docker compose logs identity-service`

### Redis Connection Issues
OTP storage requires Redis. Ensure Redis is running:
```bash
docker compose ps redis
```

## References

- [JWT.io](https://jwt.io/) - JWT introduction
- [PyJWT Documentation](https://pyjwt.readthedocs.io/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [RabbitMQ Documentation](https://www.rabbitmq.com/documentation.html)

---

**Phase 2 Completion Date:** 2024
**Status:** Complete and tested
