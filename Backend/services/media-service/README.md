# media-service

Phase 6 turns `media-service` into a secure receipt upload and download service. It stores media metadata locally, keeps projections of identity and group state, and publishes media events for the rest of the system.

## Phase 6 Overview

Phase 6 adds the core receipt flow:

- upload a receipt for a group
- inspect media metadata
- download the stored file
- list group media
- soft delete media
- consume identity and group events to keep local projections in sync
- publish media lifecycle events

This phase intentionally focuses on infrastructure, security, and media bookkeeping. It does not implement expense attachment, OCR, settlement logic, or any frontend work.

## Architecture

The service follows a layered structure:

- API layer: thin DRF views and serializers
- Application layer: use cases and orchestration services
- Domain layer: media models, projections, access rules, and events
- Infrastructure layer: JWT authentication, RabbitMQ, storage providers, and repository access

The application layer coordinates validation, projection checks, checksum generation, file storage, database persistence, access logging, and event publishing.

## Projection Strategy

`media-service` does not query identity-service or group-service directly for every request. Instead, it maintains local projections populated from RabbitMQ events:

- `UserProjection` mirrors identity-service users
- `GroupProjection` mirrors groups
- `GroupMemberProjection` mirrors membership and role state

This keeps media authorization checks fast and resilient to transient upstream outages.

## Identity Event Consumption

Identity events are consumed by the media consumer and used to upsert user projections.

Supported identity events include:

- `UserCreated`
- `UserUpdated`

These events update the local `UserProjection` table.

Run the identity consumer directly with:

```powershell
python manage.py consume_identity_events
```

## Group Event Consumption

Group events keep group and membership projections in sync.

Supported group events include:

- `GroupCreated`
- `GroupUpdated`
- `GroupArchived`
- `GroupMemberJoined`
- `GroupMemberRemoved`
- `GroupMemberLeft`

Run the group consumer directly with:

```powershell
python manage.py consume_group_events
```

Or run both consumers together:

```powershell
python manage.py consume_events
```

## Storage Provider Abstraction

Media storage is abstracted behind a `StorageProvider` interface so the service can support different Backends without changing the upload and download flow.

Current providers:

- `LocalStorageProvider` for Phase 6
- placeholders for S3 and MinIO

In Phase 6, the local provider stores files under `MEDIA_ROOT`.

## Local Storage Setup

Docker Compose mounts a persistent volume at `/media/uploads` so files survive container restarts.

The default local storage settings are:

- `MEDIA_STORAGE_PROVIDER=local`
- `MEDIA_ROOT=/media/uploads`

## File Validation Rules

Uploaded files are validated before they are saved.

Validation checks:

- file size must not exceed `MEDIA_MAX_FILE_SIZE_BYTES`
- extension must be in `MEDIA_ALLOWED_EXTENSIONS`
- content type must be in `MEDIA_ALLOWED_CONTENT_TYPES`
- unsafe executable/script-like extensions are rejected

Default limits:

- `MEDIA_MAX_FILE_SIZE_BYTES=5242880`
- `MEDIA_ALLOWED_EXTENSIONS=jpg,jpeg,png,webp,pdf`
- `MEDIA_ALLOWED_CONTENT_TYPES=image/jpeg,image/png,image/webp,application/pdf`

## Secure Filename Strategy

The service does not use the original filename as the stored filename.

Stored media uses a random object key shape like:

```text
receipts/{group_id}/{year}/{month}/{uuid}.{extension}
```

This reduces filename collisions and avoids leaking user-supplied names into storage paths.

## Checksum Strategy

After the upload is read, the service calculates `checksum_sha256` from the raw file bytes and stores it with the media record.

This helps with integrity checks and future deduplication workflows.

## Access Control Rules

All protected endpoints require a valid JWT.

Access rules:

- upload: active group member only
- detail: active group member only
- download: active group member only
- list: active group member only
- delete: uploader, group OWNER, or group ADMIN
- deleted media cannot be accessed again

Group status must be `ACTIVE` for upload and list flows.

## MediaAccessLog Purpose

Every media action creates an audit record in `MediaAccessLog`.

Logged actions:

- `UPLOAD`
- `VIEW`
- `DOWNLOAD`
- `DELETE`

These logs provide traceability for access and lifecycle events.

## Media Event Publishing

The service publishes media lifecycle events to RabbitMQ using the `hamdong.media` exchange.

Routing keys:

- `media.uploaded`
- `media.deleted`

Published events are versioned and use a consistent envelope. Publishing failures are logged and should not crash the main API flow.

## Docker Compose Usage

Phase 6 adds a dedicated consumer service in Docker Compose:

- `media-service` runs the API
- `media-consumer` runs event consumption
- `media_uploads` persists local file storage

Typical run commands:

```powershell
docker compose up media-service media-consumer
```

If you want the consumers split out manually instead, the commands are:

```powershell
python manage.py consume_identity_events
python manage.py consume_group_events
```

## Endpoint Examples

Upload a receipt:

```http
POST /api/v1/media/receipts/
Authorization: Bearer <access_token>
Content-Type: multipart/form-data

group_id=<uuid>
related_expense_id=<uuid|null>
file=<binary>
```

Get media detail:

```http
GET /api/v1/media/files/{file_id}/
Authorization: Bearer <access_token>
```

Download media:

```http
GET /api/v1/media/files/{file_id}/download/
Authorization: Bearer <access_token>
```

List group media:

```http
GET /api/v1/media/groups/{group_id}/media/?file_type=RECEIPT&page=1&page_size=20
Authorization: Bearer <access_token>
```

Delete media:

```http
DELETE /api/v1/media/files/{file_id}/
Authorization: Bearer <access_token>
```

## Testing

Run the focused Phase 6 tests:

```powershell
pytest apps/media_files/tests/test_phase6.py -q
```

Run inside Docker if you want the service environment:

```powershell
docker compose run --rm --build media-service pytest apps/media_files/tests/test_phase6.py -q
```

## Explicitly Not Included

Phase 6 does not implement:

- OCR
- automatic receipt parsing
- settlement logic
- payment logic
- wallet logic
- reminder logic
- frontend work
- full expense-service receipt attachment
- receipt approval workflows
- image transformations or thumbnail generation
