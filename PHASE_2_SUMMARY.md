# Phase 2 Implementation Summary

## Overview
Phase 2 of the HamDong backend implements a complete identity service with OTP-based authentication, JWT tokens, user management, and event publishing.

## Files Created/Modified

### Domain Layer
- `apps/identity/domain/models.py` - User and RefreshToken models
- `apps/identity/domain/events.py` - Domain events (UserOtpRequested, UserCreated, UserLoggedIn, UserUpdated)
- `apps/identity/domain/rules.py` - Business rules (PhoneNumberRule, OtpRule)

### Infrastructure Layer
- `apps/identity/infrastructure/redis_otp_store.py` - Redis OTP storage with SHA256 hashing
- `apps/identity/infrastructure/rabbitmq_publisher.py` - RabbitMQ event publishing
- `apps/identity/infrastructure/key_loader.py` - JWT key loading from filesystem
- `apps/identity/infrastructure/repositories.py` - Data access layer (UserRepository, RefreshTokenRepository)

### Application Layer
- `apps/identity/application/otp_service.py` - OTP generation and verification
- `apps/identity/application/token_service.py` - JWT token generation and verification with JWKS support
- `apps/identity/application/user_service.py` - User CRUD operations
- `apps/identity/application/use_cases.py` - Use cases orchestrating services and publishing events

### API Layer
- `apps/identity/api/views.py` - All endpoint implementations
- `apps/identity/api/serializers.py` - Request/response validation
- `apps/identity/api/permissions.py` - Custom JWT authentication permission
- `apps/identity/api/urls.py` - URL routing

### Management Commands
- `apps/identity/management/commands/generate_keys.py` - RSA key generation for JWT signing

### Database
- `apps/identity/migrations/0001_initial.py` - Initial migration with User and RefreshToken models

### Tests
- `apps/identity/tests/test_otp_request.py` - OTP request and verification tests
- `apps/identity/tests/test_token_refresh.py` - Token refresh and logout tests
- `apps/identity/tests/test_me.py` - User profile endpoints tests

### Documentation
- `apps/identity/README.md` - Comprehensive Phase 2 documentation
- `config/settings/base.py` - Added JWT and OTP configuration
- `config/urls.py` - Updated with identity service endpoints
- `.env` - Added JWT and OTP environment variables
- `requirements.txt` - Added PyJWT, cryptography, phonenumbers dependencies

## Setup and Execution

### 1. Install Dependencies
```bash
docker compose exec identity-service pip install -r requirements.txt
```

Or rebuild the image:
```bash
docker compose build identity-service
```

### 2. Generate JWT Keys
```bash
docker compose exec identity-service python manage.py generate_keys
```

This creates RSA keys in `/app/keys/` directory (inside the container).

### 3. Run Migrations
```bash
docker compose exec identity-service python manage.py migrate
```

### 4. Start the Service
```bash
docker compose up identity-service
```

Or full stack:
```bash
docker compose up
```

The service will be available at:
- API: `http://localhost:8001`
- Swagger Docs: `http://localhost:8001/api/docs/`
- Health Check: `http://localhost:8001/health/`

### 5. Run Tests
```bash
# All tests
docker compose exec identity-service pytest apps/identity/tests/ -v

# With coverage
docker compose exec identity-service pytest apps/identity/tests/ --cov=apps.identity --cov-report=html

# Specific test file
docker compose exec identity-service pytest apps/identity/tests/test_otp_request.py -v
```

## Key Features Implemented

### ✅ OTP Authentication
- [x] OTP request with rate limiting
- [x] OTP verification with max attempts
- [x] Secure OTP hashing with SHA256
- [x] OTP storage in Redis
- [x] Debug mode for development
- [x] Resend cooldown

### ✅ JWT Tokens
- [x] RS256 signing with RSA keys
- [x] Access tokens (15 minutes)
- [x] Refresh tokens (7 days)
- [x] Token refresh with rotation
- [x] Token revocation on logout
- [x] JWKS endpoint for public key
- [x] Refresh token hashing before DB storage

### ✅ User Management
- [x] Custom User model with UUID
- [x] Phone number as unique identifier
- [x] User creation on first login
- [x] Phone verification tracking
- [x] Last login timestamp
- [x] Profile update (display name, names, avatar)
- [x] User role support
- [x] Soft delete support

### ✅ Events and Publishing
- [x] UserOtpRequested event
- [x] UserCreated event
- [x] UserLoggedIn event
- [x] UserUpdated event
- [x] RabbitMQ integration
- [x] Topic exchange with routing keys
- [x] Non-blocking event publishing

### ✅ API Endpoints
- [x] POST /api/v1/auth/otp/request/
- [x] POST /api/v1/auth/otp/verify/
- [x] POST /api/v1/auth/token/refresh/
- [x] POST /api/v1/auth/logout/
- [x] GET /api/v1/auth/jwks/
- [x] GET /api/v1/users/me/
- [x] PATCH /api/v1/users/me/update/

### ✅ Testing
- [x] OTP flow tests
- [x] Token management tests
- [x] User profile tests
- [x] Edge case and error handling
- [x] Rate limiting tests
- [x] Token rotation tests

### ✅ Documentation
- [x] Service README with examples
- [x] API documentation in Swagger
- [x] Setup instructions
- [x] Troubleshooting guide

## Example cURL Commands

### Request OTP
```bash
curl -X POST http://localhost:8001/api/v1/auth/otp/request/ \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "09123456789"}'
```

### Verify OTP
```bash
curl -X POST http://localhost:8001/api/v1/auth/otp/verify/ \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "09123456789", "code": "123456"}'
```

### Get Current User
```bash
curl http://localhost:8001/api/v1/users/me/ \
  -H "Authorization: Bearer <access_token>"
```

### Update Profile
```bash
curl -X PATCH http://localhost:8001/api/v1/users/me/update/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"display_name": "Ali Ahmadi", "first_name": "Ali", "last_name": "Ahmadi"}'
```

### Refresh Token
```bash
curl -X POST http://localhost:8001/api/v1/auth/token/refresh/ \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "<refresh_token>"}'
```

### Get JWKS
```bash
curl http://localhost:8001/api/v1/auth/jwks/
```

## Architecture Decisions

### Why RS256?
- Asymmetric signing allows other services to validate tokens locally without calling identity service
- Private key stays in identity service only
- Better for distributed microservices

### Why OTP Storage Hashing?
- Even if Redis is compromised, raw OTP codes are not exposed
- SHA256 is fast enough for verification

### Why Token Hashing?
- If PostgreSQL is compromised, refresh tokens cannot be used directly
- Prevents token reuse after logout

### Why Event Publishing?
- Loose coupling between services
- Other services can react to user lifecycle events (Phase 3+)
- Audit trail for user actions

### Why Clean Architecture?
- Clear separation of concerns
- Easy to test each layer independently
- Easy to replace infrastructure components (e.g., switch from Redis to Memcached)
- Domain logic is independent of frameworks

## Not Implemented in Phase 2

- Real SMS sending (Phase 3)
- Email verification
- Password-based login
- Social login (OAuth)
- Multi-factor authentication
- Admin user management UI
- User deletion (soft delete only)
- Session management
- Email notifications

## Environment Configuration

Key environment variables for Phase 2:

```env
# JWT
JWT_ALGORITHM=RS256
JWT_ISSUER=hamdong.identity-service
JWT_AUDIENCE=hamdong.services
JWT_ACCESS_TOKEN_LIFETIME_SECONDS=900
JWT_REFRESH_TOKEN_LIFETIME_SECONDS=604800
JWT_PRIVATE_KEY_PATH=/app/keys/private.pem
JWT_PUBLIC_KEY_PATH=/app/keys/public.pem

# OTP
OTP_LENGTH=6
OTP_TTL_SECONDS=120
OTP_RESEND_COOLDOWN_SECONDS=60
OTP_MAX_VERIFY_ATTEMPTS=5
OTP_MAX_REQUESTS_PER_WINDOW=3
OTP_RATE_LIMIT_WINDOW_SECONDS=600
OTP_DEBUG_RETURN_CODE=true  # Set to false in production!

# RabbitMQ Events
IDENTITY_RABBITMQ_EXCHANGE=hamdong.identity
```

## Testing Results

All test suites should pass:

```bash
$ pytest apps/identity/tests/ -v

test_otp_request.py::OtpRequestTestCase::test_request_otp_with_valid_phone PASSED
test_otp_request.py::OtpRequestTestCase::test_request_otp_with_invalid_phone PASSED
test_otp_request.py::OtpRequestTestCase::test_request_otp_rate_limit PASSED
test_otp_request.py::OtpVerifyTestCase::test_verify_otp_creates_new_user PASSED
test_otp_request.py::OtpVerifyTestCase::test_verify_otp_logs_in_existing_user PASSED
test_otp_request.py::OtpVerifyTestCase::test_verify_otp_with_wrong_code PASSED
test_otp_request.py::OtpVerifyTestCase::test_verify_otp_expired PASSED
test_otp_request.py::OtpVerifyTestCase::test_verify_otp_max_attempts PASSED
test_token_refresh.py::TokenRefreshTestCase::test_refresh_token_success PASSED
test_token_refresh.py::TokenRefreshTestCase::test_refresh_token_rotation PASSED
test_token_refresh.py::TokenRefreshTestCase::test_refresh_token_reuse_fails PASSED
test_token_refresh.py::LogoutTestCase::test_logout_success PASSED
test_token_refresh.py::LogoutTestCase::test_logout_revokes_token PASSED
test_me.py::GetCurrentUserTestCase::test_get_current_user_with_valid_token PASSED
test_me.py::UpdateCurrentUserTestCase::test_update_current_user_display_name PASSED
...
```

## Next Steps (Phase 3)

- Real SMS integration
- Email verification
- Notification service consumers
- User deletion endpoint
- Admin user management
- Permission-based access control
- OAuth integration
- Rate limiting middleware for all endpoints
- API key authentication for service-to-service calls

## Support

For issues or questions, check:
1. [apps/identity/README.md](./README.md) - Detailed service documentation
2. Swagger UI at `/api/docs/`
3. Test files for usage examples
4. Service logs: `docker compose logs -f identity-service`