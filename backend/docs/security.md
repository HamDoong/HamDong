# Security

## JWT with RS256

identity-service signs access and refresh tokens with RS256. Protected services verify access tokens with a public key or JWKS.

## Key Ownership

The private key belongs only to identity-service. Verifier services use the public key path or JWKS URL.

## Access Token Claims

Access tokens include `sub`, `phone_number`, `role`, `type`, `jti`, `iat`, `exp`, `iss`, and `aud`. Protected services validate issuer, audience, expiration, issued-at, token type, subject, and JWT ID.

## Refresh Token Hashing

Refresh tokens are stored as hashes. Rotation revokes the old token, and logout revokes the active refresh token.

## OTP Hashing and Expiration

Raw OTP values are not stored. OTP values are hashed and expire after the configured TTL. Resend cooldown and rate-limit settings reduce abuse.

## OTP Logging

Raw OTP values are not logged. In local debug mode, `debug_otp` can be returned for manual testing. Production should run with `DEBUG=false`.

## Invite Token Hashing

Group invite tokens are stored in hashed form where implemented, limiting exposure if storage is inspected.

## File Validation

media-service validates uploaded receipt files, stores random filenames, and tracks checksums for integrity and traceability.

## Group Permissions

Protected group, expense, media, and settlement endpoints require an authenticated user and group membership where appropriate.

## No Direct Cross-service Database Access

Services use events and local projections rather than reading another service database.

## Environment Secrets

Secrets belong in local `.env` files or deployment secret stores. `.env.example` files contain placeholders only.

## Phone Masking

Phone numbers should be masked in logs and notification records where possible.

## Swagger in Production

Swagger and schema endpoints are helpful for development and academic review. Production deployments should restrict them or disable public access.
