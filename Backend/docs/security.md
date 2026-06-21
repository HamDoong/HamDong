# Security

## JWT with RS256

identity-service signs tokens with RS256. Protected services verify access tokens with the public key or JWKS and validate issuer, audience, subject, type, expiration, issued-at, and JWT ID.

## Private Key Ownership

The private signing key must exist only in identity-service. Verifier services should never carry the private key. They consume the public key through a mounted file path or `IDENTITY_JWKS_URL`.

## Access Token Claims

Current access-token validation expects claims such as `sub`, `email`, `role`, `type`, `jti`, `iat`, `exp`, `iss`, and `aud`.

## Refresh Token Hashing

Refresh tokens are stored as hashes, not as raw token strings. Rotation replaces the old record and logout revokes the active refresh token.

## OTP Hashing

Raw OTP values are not stored in the database. identity-service stores only hashed/derived verification state plus TTL and rate-limit metadata.

## OTP Expiration

OTP codes expire after the configured `OTP_TTL_SECONDS`. Resend cooldown is controlled by `OTP_RESEND_COOLDOWN_SECONDS`.

## OTP Rate Limit

Request throttling and verification-attempt limits are controlled by `OTP_MAX_REQUESTS_PER_WINDOW`, `OTP_RATE_LIMIT_WINDOW_SECONDS`, and `OTP_MAX_VERIFY_ATTEMPTS`.

## Raw OTP Handling

Raw OTP values must not be stored in the database and must not be written to normal logs. Local debug responses may include `debug_otp` only when `DEBUG=true`.

## Invite Token Hashing

Group invite tokens should be stored in hashed form so a database read does not reveal reusable raw invite tokens.

## File Validation

media-service validates content type, extension, and maximum file size before storing a receipt.

## Random Stored Filename

Uploaded files are stored under randomized names rather than user-provided names to reduce guessing and collision risks.

## Checksum

media-service records checksums so uploads can be tracked and validated for integrity.

## Group Permissions

Expense, media, and settlement endpoints require a valid JWT and appropriate group membership/role checks before a user can act on group resources.

## No Direct Cross-service DB Access

Services do not read another service database directly. They use events and local projections instead, which limits accidental privilege expansion across service boundaries.

## Production `DEBUG=false`

Production deployments should run with `DEBUG=false`. Debug-only helpers such as returning `debug_otp` are for local/demo use only.

## Environment Secrets

Keep secrets in local `.env` files or a deployment secret store. `.env.example` files must keep placeholder values only. Do not commit real SMS credentials or real private-key content.

## Phone Masking

Phone numbers should be masked in logs, notification records, and operator tooling where possible.

## Swagger Restriction Recommendation

Swagger and schema endpoints are useful during development and demos. Production environments should restrict or disable public access to them.
