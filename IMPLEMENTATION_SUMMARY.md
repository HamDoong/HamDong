"""Implementation Summary - HamDong IAM Service OTP Request Feature

This document provides a complete overview of the backend implementation for the
HamDong OTP Request feature following Clean Architecture principles.
"""

# ============================================================================
# PROJECT STRUCTURE
# ============================================================================

"""
HamDong/
└── iam-service/
    ├── src/
    │   ├── domain/                    # Business logic layer
    │   │   ├── entities/
    │   │   │   └── __init__.py       # OTPEntity, UserEntity
    │   │   ├── interfaces/
    │   │   │   └── __init__.py       # Repository & Service interfaces
    │   │   └── exceptions/
    │   │       └── __init__.py       # Domain exceptions
    │   │
    │   ├── application/               # Application logic layer
    │   │   ├── dtos/
    │   │   │   └── __init__.py       # OTPRequestDTO, OTPResponseDTO
    │   │   └── use_cases/
    │   │       └── request_otp.py    # RequestOTPUseCase
    │   │
    │   ├── infrastructure/            # External integrations layer
    │   │   ├── redis/
    │   │   │   └── otp_repository.py # RedisOTPRepository
    │   │   ├── resilience/
    │   │   │   └── rate_limiter.py   # RedisRateLimiter
    │   │   ├── services/
    │   │   │   ├── otp_service.py    # OTPService
    │   │   │   └── sms_service.py    # MockSMSService, TwilioSMSService
    │   │   ├── database/
    │   │   ├── security/
    │   │   └── __init__.py
    │   │
    │   ├── presentation/              # HTTP API layer
    │   │   ├── api/v1/
    │   │   │   ├── auth.py           # OTP endpoints
    │   │   │   └── __init__.py
    │   │   ├── dependencies/
    │   │   │   └── __init__.py       # Dependency injection
    │   │   └── __init__.py
    │   │
    │   ├── configuration/
    │   │   └── settings.py           # App configuration
    │   │
    │   └── main.py                   # FastAPI app factory
    │
    ├── tests/
    │   ├── conftest.py               # Pytest fixtures & configuration
    │   ├── unit/
    │   │   ├── application/
    │   │   │   └── use_cases/
    │   │   │       └── test_request_otp.py
    │   │   └── infrastructure/
    │   │       ├── test_otp_service.py
    │   │       └── test_rate_limiter.py
    │   ├── integration/
    │   │   └── test_otp_repository.py
    │   └── api/
    │       └── test_auth.py
    │
    ├── requirements.txt              # Python dependencies
    ├── pytest.ini                    # Pytest configuration
    ├── .env.example                  # Environment variables template
    ├── Dockerfile                    # Docker image definition
    ├── docker-compose.yml            # Local development stack
    ├── Makefile                      # Common commands
    ├── README.md                     # Project documentation
    ├── CONTRIBUTING.md               # Contributing guidelines
    └── .gitignore                    # Git ignore rules
"""

# ============================================================================
# KEY FILES & COMPONENTS
# ============================================================================

# --- DOMAIN LAYER ---

# src/domain/entities/__init__.py
"""
Contains domain entities representing core business objects:

OTPEntity:
  - Represents a generated OTP for authentication
  - Methods: is_expired(), increment_attempts()
  - Properties: phone_number, otp_hash, expires_at, attempts

UserEntity:
  - Represents a user in the system
  - Properties: user_id, phone_number, verified
"""

# src/domain/interfaces/__init__.py
"""
Defines contracts for external services:

OTPRepositoryInterface:
  - save(otp): Store OTP
  - get_by_phone(phone): Retrieve OTP
  - delete_by_phone(phone): Remove OTP

RateLimiterInterface:
  - check_rate_limit(key, limit, window): Check if limit exceeded
  - increment_counter(key, window): Increment counter

OTPServiceInterface:
  - generate_otp(): Create random OTP
  - hash_otp(otp): Hash OTP code
  - verify_otp(otp, hash): Verify OTP against hash

SMSServiceInterface:
  - send_otp_sms(phone, otp): Send SMS message
"""

# src/domain/exceptions/__init__.py
"""
Domain-level exceptions:

DomainException (base)
  ├─ ValidationException
  ├─ RateLimitException
  ├─ OTPException
  └─ AuthenticationException
"""

# --- APPLICATION LAYER ---

# src/application/dtos/__init__.py
"""
Data Transfer Objects for API communication:

OTPRequestDTO:
  - phone_number: str (validated, 10-15 digits, starts with 0)

OTPResponseDTO:
  - message: str
  - expires_in: int (seconds)

OTPVerificationDTO:
  - phone_number: str
  - otp: str

OTPInternalDTO:
  - Internal data transfer between layers
"""

# src/application/use_cases/request_otp.py
"""
RequestOTPUseCase - Main business logic orchestrator:

execute(request, client_ip) -> OTPResponseDTO:
  1. Validate phone number format
  2. Check rate limits (per phone: 3/5min, per IP: 10/1min)
  3. Generate 6-digit OTP
  4. Hash OTP with HMAC-SHA256
  5. Store in Redis with 120s TTL
  6. Send SMS asynchronously
  7. Return success response

Constants:
  - OTP_REQUESTS_PER_PHONE = 3
  - OTP_REQUESTS_WINDOW_PHONE = 5 * 60 seconds
  - OTP_REQUESTS_PER_IP = 10
  - OTP_REQUESTS_WINDOW_IP = 60 seconds
  - OTP_TTL_SECONDS = 120
"""

# --- INFRASTRUCTURE LAYER ---

# src/infrastructure/redis/otp_repository.py
"""
RedisOTPRepository - Implements OTPRepositoryInterface:

Redis Key Format: otp:{phone_number}
Redis Value: JSON with otp_hash, expires_at, attempts
TTL: Automatic expiration based on expires_at

Methods:
  - save(otp): Store OTP in Redis with TTL
  - get_by_phone(phone): Retrieve and deserialize OTP
  - delete_by_phone(phone): Delete OTP record
"""

# src/infrastructure/resilience/rate_limiter.py
"""
RedisRateLimiter - Implements RateLimiterInterface:

Sliding window counter using Redis INCR + EXPIRE

Redis Key Format: rate_limit:{key}

Methods:
  - check_rate_limit(key, limit, window): Check if limit exceeded
  - increment_counter(key, window): Increment counter
"""

# src/infrastructure/services/otp_service.py
"""
OTPService - Implements OTPServiceInterface:

OTP Configuration:
  - Length: 6 digits
  - Hashing: HMAC-SHA256
  - Verification: Timing-safe comparison

Methods:
  - generate_otp(): Random 6-digit code
  - hash_otp(otp): HMAC-SHA256 hash
  - verify_otp(otp, hash): Timing-safe verify
"""

# src/infrastructure/services/sms_service.py
"""
SMS Service implementations:

MockSMSService:
  - For development/testing
  - Logs OTP to console

TwilioSMSService:
  - Production SMS provider
  - Requires: account_sid, auth_token, from_phone
"""

# --- PRESENTATION LAYER ---

# src/presentation/dependencies/__init__.py
"""
Dependency Injection setup:

get_redis_client():
  - Returns Redis async client
  - Singleton pattern

get_otp_use_case():
  - Assembles all dependencies
  - Returns RequestOTPUseCase instance
  - Called by FastAPI dependency injection
"""

# src/presentation/api/v1/auth.py
"""
Authentication API endpoints:

POST /api/v1/auth/otp/request:
  - Request body: {phone_number: str}
  - Response: {message: str, expires_in: int}
  - Status: 200 OK
  - Errors: 400 (validation), 429 (rate limit), 500 (server error)
  - Logging: Request ID, phone number, client IP
"""

# --- CONFIGURATION ---

# src/configuration/settings.py
"""
Application settings with Pydantic:

Environment variables:
  - app_name, app_version, debug
  - host, port
  - database_url, redis_url
  - jwt_secret_key, otp_secret_key
  - otp_ttl_seconds, otp_length
  - rate limiting thresholds
  - sms_provider configuration
  - log_level

Default values provided, loaded from .env
"""

# src/main.py
"""
FastAPI application factory:

create_app():
  - Initializes FastAPI instance
  - Includes routers
  - Sets up exception handlers
  - Registers health check endpoint
  - Configures lifespan events

Health check: GET /health
"""

# ============================================================================
# TESTS
# ============================================================================

"""
tests/conftest.py:
  - Pytest fixtures for mock Redis
  - OTP service fixture
  - SMS service fixture
  - Repository fixtures
  - Sample data fixtures

tests/unit/application/use_cases/test_request_otp.py:
  - 8 test cases for RequestOTPUseCase
  - Tests success flow
  - Tests rate limit failures (phone & IP)
  - Tests invalid phone formats
  - Tests SMS failures (non-blocking)

tests/unit/infrastructure/test_otp_service.py:
  - 7 test cases for OTPService
  - Tests OTP generation uniqueness
  - Tests deterministic hashing
  - Tests OTP verification (success & failure)
  - Tests timing-safe comparison

tests/unit/infrastructure/test_rate_limiter.py:
  - Tests rate limit checks
  - Tests counter increments
  - Tests first-time vs subsequent increments

tests/integration/test_otp_repository.py:
  - Tests Redis OTP storage
  - Tests retrieval and deserialization
  - Tests deletion

tests/api/test_auth.py:
  - 7 test cases for API endpoints
  - Tests successful OTP request
  - Tests validation errors
  - Tests rate limit responses (429)
  - Tests internal errors (500)
  - Tests missing parameters
"""

# ============================================================================
# ARCHITECTURE DECISIONS
# ============================================================================

"""
1. CLEAN ARCHITECTURE
   - Strict layer separation ensures maintainability
   - Domain layer has no framework imports
   - Easy to test each layer independently
   - Easy to swap implementations

2. REPOSITORY PATTERN
   - OTP storage abstracted behind interface
   - Can swap Redis for other storage
   - Facilitates testing with mocks

3. USE CASE PATTERN
   - Encapsulates business logic
   - Single responsibility
   - Easy to test in isolation
   - Reusable across presentations (REST, gRPC, etc.)

4. DEPENDENCY INJECTION
   - FastAPI's Depends for DI
   - Constructor injection in use cases
   - Loose coupling, easy to test

5. ASYNC/AWAIT
   - Full async support for scalability
   - Redis operations are async
   - SMS sending is non-blocking

6. RATE LIMITING STRATEGY
   - Redis sliding window counter
   - Per-phone and per-IP limits
   - Distributed system ready

7. OTP SECURITY
   - HMAC-SHA256 hashing (not plain storage)
   - Timing-safe comparison (prevents timing attacks)
   - TTL prevents indefinite validity
   - Attempt counting for brute-force protection

8. ERROR HANDLING
   - Domain exceptions for business errors
   - HTTP status codes map to error types
   - User-friendly error messages
   - SMS failures don't fail the request (resilient)

9. OBSERVABILITY
   - Structured logging with request IDs
   - Client IP tracking
   - Phone number tracking (for analytics)
   - Ready for metrics integration
"""

# ============================================================================
# RUNNING THE APPLICATION
# ============================================================================

"""
DEVELOPMENT:
1. Copy .env.example to .env
2. Adjust configuration as needed
3. Run: docker-compose up
4. Start server: make dev
5. API docs: http://localhost:8000/docs

TESTING:
1. Run all tests: make test
2. Run with coverage: make test-coverage
3. Run unit tests only: make test-unit
4. Run API tests only: make test-api

DEPLOYMENT:
1. Build Docker image: docker build -t hamdong-iam:1.0.0 .
2. Set production environment variables
3. Run container with proper secrets
"""

# ============================================================================
# SECURITY CONSIDERATIONS
# ============================================================================

"""
✓ Implemented:
  - OTP hashing with HMAC-SHA256
  - Timing-safe OTP verification
  - Rate limiting (brute-force protection)
  - Input validation (Pydantic)
  - Error messages don't leak system details

⚠ Future implementation:
  - JWT for API authentication
  - RBAC for authorization
  - Session management with refresh tokens
  - Audit logging
  - IP whitelist/blacklist
  - Account lockout after failed attempts
  - CORS configuration
  - SQL injection prevention (via ORM)
  - CSRF protection
"""

# ============================================================================
# PERFORMANCE CONSIDERATIONS
# ============================================================================

"""
✓ Implemented:
  - Redis caching for OTP data
  - Async operations throughout
  - Non-blocking SMS sending
  - Automatic OTP expiration (TTL)
  - Efficient rate limiting (Redis INCR)

⚠ Future optimization:
  - Database connection pooling
  - Redis connection pooling
  - Metrics collection
  - Query optimization
  - Caching strategies
  - Load testing
  - CDN for static assets
"""

# ============================================================================
# NEXT STEPS FOR DEVELOPMENT
# ============================================================================

"""
Phase 2 - OTP Verification:
  - Endpoint: POST /api/v1/auth/otp/verify
  - Verify OTP code against stored hash
  - Increment attempt counter
  - Lock after max attempts

Phase 3 - User Registration:
  - Create user after verified OTP
  - Hash password with bcrypt
  - Generate JWT token

Phase 4 - Authentication:
  - JWT token validation
  - Refresh token mechanism
  - Session management

Phase 5 - Authorization:
  - RBAC implementation
  - Permission checking
  - Role management

Phase 6 - Advanced Features:
  - Multi-factor authentication
  - Social login
  - API keys
  - OAuth2
"""

# ============================================================================
# TESTING COVERAGE
# ============================================================================

"""
Target: 80%+ code coverage

Current coverage areas:
  ✓ Use case logic
  ✓ OTP generation and hashing
  ✓ Rate limiting
  ✓ API endpoints
  ✓ Error handling
  ✓ Repository operations

Run coverage: pytest --cov=src --cov-report=html
"""

print(__doc__)
