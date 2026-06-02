# Security

This document outlines security practices used across services.

- JWT with RS256: Services validate access tokens using RS256 public keys served by `identity-service` JWKS. Public key validation ensures tokens are verifiable without sharing private keys.
- Refresh token hashing: refresh tokens are hashed in the DB to prevent theft of raw tokens.
- OTP hashing: OTP values are not stored in plaintext; hashed or ephemeral storage is used. Raw OTPs are never logged.
- OTP expiration and rate limits: OTP lifetime and request/verify rate limits are enforced to prevent abuse.
- Invite tokens: raw invite token is not stored; the server stores a derived hash and compares safely.
- File validation: uploaded files are validated by extension and content type; stored file names are randomized and checksums recorded.
- Group permissions: owner/admin/member permissions enforced in APIs; membership required to access group resources.
- No direct cross-service DB access: services interact via events and APIs only.
- Environment secrets: store in `.env` and CI secrets; do not commit to git.
- Production settings: `DEBUG=false`, restricted CORS, and Swagger/docs access can be limited in production.
- Phone masking: logs should mask phone numbers to avoid leaking PII.
- Event idempotency: Inbox/ProcessedEvent tables prevent duplicate processing.
- Outbox/Inbox reliability: Outbox ensures messages are persisted in the producer DB before publishing.
