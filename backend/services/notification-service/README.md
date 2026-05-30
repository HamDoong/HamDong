# Notification Service

Phase 3 turns notification-service into the OTP SMS delivery worker for HamDong.
It consumes `SendOtpSmsRequested` commands from RabbitMQ, sends SMS through a provider abstraction, and persists delivery state in `notification_db`.

## Architecture

- `identity-service` requests OTPs and publishes `SendOtpSmsRequested` to `hamdong.identity` with routing key `identity.otp.requested`.
- `notification-consumer` binds to `notification.identity.otp.requested` and consumes those commands.
- `notification-service` exposes local/debug API endpoints and stores notification state.
- `notification_db` stores `NotificationMessage`, `SmsTemplate`, and `ProviderDeliveryLog` records.

## RabbitMQ Topology

- Exchange: `hamdong.identity`
- Routing key: `identity.otp.requested`
- Queue: `notification.identity.otp.requested`
- Dead Letter Exchange: `notification.identity.otp.requested.dlx`
- Dead Letter Queue: `notification.identity.otp.requested.dlq`

The consumer declares the queue with dead-letter settings so failed OTP messages can be routed to the DLQ after the limited retry policy is exhausted.

## SMS Providers

Supported providers are selected with `SMS_PROVIDER`:

- `fake` for local development and tests
- `kavenegar` for a real HTTP adapter
- `melipayamak` for a real HTTP adapter

The provider adapters read `SMS_API_KEY` and `SMS_SENDER` from the environment. Invalid provider names are rejected with a controlled `INVALID_SMS_PROVIDER` error.

## Circuit Breaker

The SMS provider call is wrapped by `pybreaker` with:

- `SMS_CIRCUIT_FAIL_MAX=5`
- `SMS_CIRCUIT_RESET_TIMEOUT_SECONDS=60`

When the breaker is open, the consumer does not call the provider, marks the notification as failed, and routes the message according to the retry/DLQ policy.

## Retry Policy

OTP messages use a limited retry policy:

- `SMS_OTP_MAX_RETRIES=2`
- `SMS_OTP_RETRY_DELAYS_SECONDS=10,30`

If the OTP expires before a retry can complete, the message is marked `SKIPPED`.

## Endpoints

- `GET /api/v1/notifications/health/`
- `POST /api/v1/notifications/sms/test/`
- `GET /api/v1/notifications/messages/` in local/debug only

The test SMS endpoint works only when `DEBUG=true` or `APP_ENV=local`.

## Local Usage

The fake provider is the default for local development:

```bash
SMS_PROVIDER=fake
```

The consumer runs as a separate Docker Compose service:

```bash
python manage.py consume_identity_events
```

## Full OTP SMS Flow

1. Request OTP from identity-service.
2. identity-service stores the OTP hash in Redis.
3. identity-service publishes `SendOtpSmsRequested` to RabbitMQ.
4. notification-consumer consumes the command.
5. notification-service sends the SMS and records the result.

## Intentionally Excluded

Phase 3 does not add:

- group invitations
- expense reminders
- settlement reminders
- push notifications
- email notifications
- wallet logic
- payment gateway logic
- frontend changes
