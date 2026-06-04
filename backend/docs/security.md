# Security

## JWT with RS256

- identity-service is the only JWT issuer and signer.
- The private key stays only inside identity-service.
- Verifier services use the public key / JWKS and validate:
  - RS256 signature
  - issuer
  - audience
  - token type
  - `sub`
  - `jti`
  - `iat`
  - `exp`

## Refresh Token Hashing

- refresh tokens are stored hashed
- raw refresh tokens are not stored in the database
- rotation revokes the previous token
- logout revokes active refresh tokens

## OTP Security

- OTP values are stored hashed or in ephemeral secure form
- OTP has expiration
- OTP request/verify rate limits are configurable
- raw OTP values are not stored in DB
- raw OTP values are not logged
- `debug_otp` is intended only for local `DEBUG=true` use

## OTP Expiration and Rate Limit

Key settings in `.env.example`:

- `OTP_LENGTH`
- `OTP_TTL_SECONDS`
- `OTP_RESEND_COOLDOWN_SECONDS`
- `OTP_MAX_VERIFY_ATTEMPTS`
- `OTP_MAX_REQUESTS_PER_WINDOW`
- `OTP_RATE_LIMIT_WINDOW_SECONDS`

## Invite Token Hashing

Invite handling uses token protection / hashing so that raw invite secrets are not treated like normal IDs.

## File Validation

Media upload security includes:

- content type validation
- max file size limits
- randomized stored file name
- checksum / integrity metadata where applicable
- access control through authenticated membership

## Group Membership Permissions

Group, expense, media, and settlement endpoints check authenticated membership/role before allowing access to sensitive group data.

## Cross-service Data Access

- services do not read each other’s databases directly
- cross-service data is exchanged through HTTP or RabbitMQ events
- projections are stored locally per service

## Operational Security

- production should run with `DEBUG=false`
- secrets should be kept in environment files or secret managers, not committed real values
- phone numbers are masked in logs where applicable
- SMS delivery logs should avoid leaking sensitive data
