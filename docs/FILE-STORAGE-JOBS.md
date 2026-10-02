# Shared image storage and welcome mail (Issue #45)

This module implements FR-FILE-001, FR-JOB-001, and the shared-storage part of
NFR-SCALE-001. The application is Python/FastAPI, so a PostgreSQL outbox plus a
separate worker provides the persistent job behavior described by the SRS.

## Image-storage contract for Issue #43

`S3FileStorage` in `backend/src/culinary_blog_api/storage/service.py` exposes:

```python
url = await storage.upload_file(upload_file, f"recipes/{recipe_id}")
stored = await storage.read(url)  # bytes + content_type
await storage.delete(url)         # repeated deletes are safe
```

`upload_image(data, folder, content_type)` is available when the caller already
has bytes. It creates `{folder}/{uuid}.{ext}` in the configured bucket and
returns a public URL. The adapter enforces a 5 MB limit and checks MIME plus
magic bytes for JPEG, PNG, WebP, and AVIF. It rejects unsafe folders and URLs
outside its public bucket prefix. The upload route, image metadata, primary
image rules, and recipe permissions belong to #43; that route should translate
`InvalidImage` to RFC 7807 `400`, `StorageNotFound` to `404`, and
`StorageUnavailable` to `503`. Transient S3 errors receive two short retries
before the adapter reports failure.

The `minio-init` Compose service creates the bucket and enables anonymous
download for local development. Compose builds the official MinIO source at
the pinned `RELEASE.2025-10-15T17-29-55Z` tag because its former public Docker
images are no longer available. The first build can take several minutes.
Production may use AWS S3 or a private MinIO
deployment by changing the environment; configure the public URL and bucket
policy there. Credentials are never included in returned URLs.

## Welcome-email outbox

Local registration inserts a `welcome_email_jobs` row in the same transaction
as the new account and tokens. The HTTP handler only writes the row; the
`email-worker` Compose service sends HTML email independently through SMTP.
Workers use PostgreSQL `FOR UPDATE SKIP LOCKED` to claim due rows. Failures
are logged by job ID and error type and retried after 1, 5, and 30 minutes.
After the fourth failed send the row becomes `Failed`. A crashed worker rolls
back its transaction, so another worker can retry. Delivery is at least once:
a process crash after SMTP accepts a message but before commit can duplicate
that message. The row records status, attempts, and the next attempt time.

The default Compose SMTP destination is Mailpit at <http://localhost:8025>.
Set `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_STARTTLS`,
`SMTP_FROM`, and `APP_PUBLIC_URL` in the root `.env` for a real provider;
Compose passes these to both the API and worker. Do not commit `.env`.

## Local checks

1. On a fresh checkout, copy `.env.example` to `.env` and choose local
   passwords, then run `.\start-all.ps1`. Keep existing PostgreSQL credentials
   if you already have a populated Compose volume. This starts PostgreSQL,
   MinIO, bucket setup, Mailpit, the API, the email worker, and the frontend.
2. Register through `POST /api/v1/auth/register`; the response should be `201`
   without waiting for SMTP. Open Mailpit and confirm the welcome message.
3. The image API in #43 will call the storage adapter. Until that integration,
   verify upload/read/delete with `backend/tests/test_storage.py`; no public
   image upload endpoint is added by #45.

Migration `20261002_0006` follows #39's `20261002_0005`. Merge #39 first,
then #45, to keep one Alembic migration chain.
