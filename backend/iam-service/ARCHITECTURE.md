# HamDong IAM Service - Architecture & Design

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           CLIENT / API GATEWAY                          │
└──────────────────────────┬──────────────────────────────────────────────┘
                           │
                           │ HTTP Request
                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      PRESENTATION LAYER                                 │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  FastAPI Controllers (auth.py)                                    │  │
│  │  ┌─────────────────────────────────────────────────────────────┐  │  │
│  │  │ POST /api/v1/auth/otp/request                              │  │  │
│  │  │  • Validate request                                        │  │  │
│  │  │  • Extract client IP                                       │  │  │
│  │  │  • Call use case                                           │  │  │
│  │  │  • Return response / handle errors                         │  │  │
│  │  └─────────────────────────────────────────────────────────────┘  │  │
│  │                                                                      │  │
│  │  Dependency Injection (dependencies/__init__.py)                   │  │
│  │  ┌─────────────────────────────────────────────────────────────┐  │  │
│  │  │ get_otp_use_case() → RequestOTPUseCase                      │  │  │
│  │  │  • Inject repositories                                      │  │  │
│  │  │  • Inject services                                          │  │  │
│  │  │  • Assemble dependencies                                    │  │  │
│  │  └─────────────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────────┘  │
└──────────────────────────┬──────────────────────────────────────────────┘
                           │
                           │ Call use case
                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      APPLICATION LAYER                                  │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  RequestOTPUseCase (request_otp.py)                              │  │
│  │                                                                  │  │
│  │  execute(request: OTPRequestDTO, client_ip: str)                │  │
│  │  ├─ 1. Validate phone number                                    │  │
│  │  ├─ 2. Check rate limits (phone & IP)                           │  │
│  │  ├─ 3. Generate OTP code                                        │  │
│  │  ├─ 4. Hash OTP with OTPService                                 │  │
│  │  ├─ 5. Store in Redis via OTPRepository                         │  │
│  │  ├─ 6. Send SMS via SMSService                                  │  │
│  │  └─ 7. Return OTPResponseDTO                                    │  │
│  │                                                                  │  │
│  │  DTOs (dtos/__init__.py)                                        │  │
│  │  ├─ OTPRequestDTO                                              │  │
│  │  ├─ OTPResponseDTO                                             │  │
│  │  └─ OTPVerificationDTO                                         │  │
│  └───────────────────────────────────────────────────────────────────┘  │
└──────────────────────────┬──────────────────────────────────────────────┘
                           │
                ┌──────────┼──────────┬──────────┐
                │          │          │          │
     Rate Limit │          │          │    SMS   │
    Check/Save │          │          │   Send   │
                │          │          │          │
                ▼          ▼          ▼          ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                      INFRASTRUCTURE LAYER                                 │
│                                                                           │
│  ┌──────────────────────┐  ┌──────────────────────┐  ┌─────────────────┐ │
│  │  Rate Limiter        │  │  OTP Repository      │  │  OTP Service    │ │
│  │ (rate_limiter.py)    │  │ (otp_repository.py)  │  │(otp_service.py) │ │
│  │                      │  │                      │  │                 │ │
│  │ Redis:               │  │ Redis:               │  │ Operations:     │ │
│  │ rate_limit:{key}     │  │ otp:{phone_number}   │  │ • Generate OTP  │ │
│  │                      │  │                      │  │ • Hash OTP      │ │
│  │ INCR/EXPIRE          │  │ JSON:                │  │ • Verify OTP    │ │
│  │                      │  │ {otp_hash,           │  │                 │ │
│  │ Methods:             │  │  expires_at,         │  │ Security:       │ │
│  │ • check_rate_limit   │  │  attempts}           │  │ • HMAC-SHA256   │ │
│  │ • increment_counter  │  │                      │  │ • Timing-safe   │ │
│  │                      │  │ TTL: 120 seconds     │  │   comparison    │ │
│  │                      │  │                      │  │                 │ │
│  │                      │  │ Methods:             │  │                 │ │
│  │                      │  │ • save(otp)          │  │                 │ │
│  │                      │  │ • get_by_phone()     │  │                 │ │
│  │                      │  │ • delete_by_phone()  │  │                 │ │
│  └──────────────────────┘  └──────────────────────┘  └─────────────────┘ │
│                                                                           │
│  ┌────────────────────────────┐                                          │
│  │   SMS Service              │                                          │
│  │ (sms_service.py)           │                                          │
│  │                            │                                          │
│  │ Implementations:           │                                          │
│  │ • MockSMSService           │                                          │
│  │   (logs to console)         │                                          │
│  │                            │                                          │
│  │ • TwilioSMSService         │                                          │
│  │   (production provider)     │                                          │
│  │                            │                                          │
│  │ Methods:                   │                                          │
│  │ • send_otp_sms()           │                                          │
│  └────────────────────────────┘                                          │
│                                                                           │
└──────────────────────────┬──────────────────────────────────────────────┘
                           │
                ┌──────────┼──────────┐
                │          │          │
                ▼          ▼          ▼
       ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐
       │   REDIS      │  │  PostgreSQL  │  │  SMS Provider   │
       │              │  │              │  │  (Twilio/Mock)  │
       │ Data:        │  │ Data:        │  │                 │
       │ • OTPs       │  │ • Users      │  │ External API    │
       │ • Rate limits│  │ • Sessions   │  │                 │
       │ • Cache      │  │ • Auth logs  │  │                 │
       └──────────────┘  └──────────────┘  └─────────────────┘
```

## Layer Dependencies

```
Presentation Layer
       │
       │ (depends on)
       ▼
Application Layer (Use Cases, DTOs)
       │
       │ (depends on)
       ▼
Domain Layer (Entities, Interfaces, Exceptions)
       │
       ├── Implemented by ──────► Infrastructure Layer
       │                          (Repositories, Services)
       │                          │
       │                          ▼
       └────► External Services (Redis, SMS, DB)
```

## Request Flow Diagram

```
┌──────────────┐
│   Client     │
└──────┬───────┘
       │ 1. POST /api/v1/auth/otp/request
       │    { "phone_number": "09123456789" }
       ▼
┌──────────────────────────────┐
│  Request Validation          │
│  • Pydantic validates format │
│  • Extract client IP         │
└──────┬───────────────────────┘
       │ 2. Validated OTPRequestDTO
       ▼
┌──────────────────────────────┐
│  RequestOTPUseCase           │
└──────┬───────────────────────┘
       │
       ├─ 3. _validate_phone_number()
       │    └─► ValidationException (if invalid)
       │
       ├─ 4. _check_rate_limits()
       │    ├─ Phone rate limit (3/5min)
       │    ├─ IP rate limit (10/1min)
       │    └─► RateLimitException (if exceeded)
       │
       ├─ 5. generate_otp()
       │    └─► "123456"
       │
       ├─ 6. hash_otp("123456")
       │    └─► SHA256 hash
       │
       ├─ 7. OTPRepository.save()
       │    └─► Redis: otp:09123456789
       │
       ├─ 8. SMSService.send_otp_sms()
       │    ├─► Non-blocking
       │    └─► Errors ignored (resilient)
       │
       └─ 9. Return OTPResponseDTO
            └─► { "message": "OTP sent", "expires_in": 120 }
       │
       ▼
┌──────────────────────────────┐
│  Response to Client          │
│  HTTP 200                    │
│  { "message": "OTP sent",   │
│    "expires_in": 120 }      │
└──────────────────────────────┘
```

## Data Models

```
OTPEntity
├── phone_number: str
├── otp_hash: str (HMAC-SHA256)
├── expires_at: datetime
├── attempts: int
└── Methods:
    ├── is_expired()
    └── increment_attempts()

UserEntity
├── user_id: str
├── phone_number: str
└── verified: bool
```

## Redis Data Structure

```
OTP Storage:
KEY: otp:09123456789
VALUE: {
  "phone_number": "09123456789",
  "otp_hash": "a1b2c3d4e5f6...",
  "expires_at": "2024-01-15T10:30:00",
  "attempts": 0
}
TTL: 120 seconds (auto-expires)

Rate Limit Storage:
KEY: rate_limit:otp:request:phone:09123456789
VALUE: 2 (counter)
TTL: 300 seconds (5 minutes)

KEY: rate_limit:otp:request:ip:192.168.1.1
VALUE: 5 (counter)
TTL: 60 seconds (1 minute)
```

## Error Handling Flow

```
Request
   │
   ├─ Validation Error (400)
   │  └─ ValidationException
   │     └─ Response: { "success": false, "error": "INVALID_PHONE_FORMAT" }
   │
   ├─ Rate Limit Error (429)
   │  └─ RateLimitException
   │     └─ Response: { "success": false, "error": "RATE_LIMIT_EXCEEDED" }
   │
   ├─ OTP Error (400)
   │  └─ OTPException
   │     └─ Response: { "success": false, "error": "OTP_ERROR" }
   │
   └─ Unexpected Error (500)
      └─ Exception
         └─ Response: { "success": false, "error": "INTERNAL_SERVER_ERROR" }
```

## Security Architecture

```
Input Validation
       │
       ├─ Pydantic DTO validation
       ├─ Phone number format check
       └─ Length constraints

Rate Limiting
       │
       ├─ Per phone (3/5min)
       ├─ Per IP (10/1min)
       └─ Brute-force protection

OTP Security
       │
       ├─ Generation: random 6-digit
       ├─ Hashing: HMAC-SHA256
       ├─ Storage: hashed only (never plain)
       ├─ TTL: 120 seconds
       └─ Verification: timing-safe comparison

Error Handling
       │
       └─ No sensitive data in responses
```

## Performance Considerations

```
Operation Latency:
├─ Validate phone:          ~1ms
├─ Check rate limits:       ~5ms (Redis)
├─ Generate OTP:            ~1ms
├─ Hash OTP:                ~5ms (HMAC-SHA256)
├─ Store in Redis:          ~5ms
├─ Send SMS (async):        ~100-500ms (non-blocking)
└─ Total response time:     ~20-30ms

Scalability:
├─ Async operations support high concurrency
├─ Redis stores only short-lived data
├─ Rate limiting works in distributed systems
└─ SMS sending doesn't block response
```

## Design Patterns Used

```
1. Clean Architecture
   ├─ Domain layer with pure business logic
   ├─ Application orchestration layer
   ├─ Infrastructure implementation layer
   └─ Presentation HTTP layer

2. Repository Pattern
   ├─ Abstract data access behind interfaces
   ├─ Easy to test with mocks
   └─ Easy to swap implementations

3. Dependency Injection
   ├─ FastAPI Depends for auto-wiring
   ├─ Constructor injection in use cases
   └─ Loose coupling

4. Use Case Pattern
   ├─ Encapsulates business logic
   ├─ Orchestrates repositories and services
   └─ Reusable across presentations

5. Data Transfer Object (DTO)
   ├─ Clear contracts between layers
   ├─ Validation at boundaries
   └─ Type safety

6. Factory Pattern
   ├─ create_app() for FastAPI setup
   └─ Centralized configuration

7. Facade Pattern
   ├─ UseCase as facade
   └─ Simplifies complex subsystems

8. Strategy Pattern
   ├─ SMSService with multiple implementations
   ├─ MockSMSService for dev/test
   └─ TwilioSMSService for production
```

## SOLID Principles Implementation

```
Single Responsibility
├─ Each class has one reason to change
├─ RequestOTPUseCase: orchestrate OTP logic only
├─ OTPService: handle OTP crypto only
└─ RateLimiter: handle rate limiting only

Open/Closed
├─ Open for extension (add new SMS providers)
├─ Closed for modification (don't change existing)
└─ Add TwilioSMSService without changing MockSMSService

Liskov Substitution
├─ All implementations follow interface contracts
├─ Can swap MockSMSService with TwilioSMSService
└─ No code changes needed

Interface Segregation
├─ Small, focused interfaces
├─ OTPRepositoryInterface has 3 methods
├─ SMSServiceInterface has 1 method
└─ Clients implement only what they need

Dependency Inversion
├─ Use cases depend on interfaces, not concrete classes
├─ Infrastructure implements interfaces
├─ Easy to mock and test
└─ Decoupled from external services
```
