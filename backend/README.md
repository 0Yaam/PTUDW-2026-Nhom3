# Culinary Blog API

This folder contains the FastAPI backend. Use the root [README](../README.md) for setup and test commands.

The API includes categories, authentication, profiles, and recipe publication under `/api/v1`.

## Lab 04 authentication and publication (Issue #38)

| Action | Authorization | Success |
| --- | --- | --- |
| `POST /api/v1/auth/google` | Google ID token in the request body | `200`, local access and refresh tokens |
| `GET /api/v1/auth/me` | Bearer token | `200`, current profile |
| `PATCH /api/v1/auth/me` | Bearer token | `200`, updated profile |
| `PATCH /api/v1/recipes/{id}/publish` | Recipe owner or Admin | `200`, published recipe |
| `PATCH /api/v1/recipes/{id}/unpublish` | Recipe owner or Admin | `200`, draft recipe |

Publishing requires at least one ingredient and one cooking step. Set
`GOOGLE_CLIENT_ID` before using Google login. API errors use RFC 7807 problem details.

## Category management (Issues #2 and #33; FR-CAT-003/004/005)

The public `GET /api/v1/categories` lists categories. Admin requests use the
`accessToken` returned by `POST /api/v1/auth/login` as `Authorization: Bearer <token>`.
The backend verifies the signature and reads the user's current role from the
database. Registration creates an Author; it does not grant Admin rights.

| Action | Request body | Success |
| --- | --- | --- |
| `POST /api/v1/categories` | `{ "name": "Món Việt", "description": "..." }` | `201`, Category object, `Location: /api/v1/categories/{slug}` |
| `PUT /api/v1/categories/{id}` | `{ "name": "Tên mới", "description": null, "slug": "ten-moi" }` | `200`, updated Category object |
| `DELETE /api/v1/categories/{id}` | None | `204`, empty response |

`name` is trimmed, 2–50 characters, and cannot contain HTML. `description` is
optional and cannot contain HTML. On update, `slug` is optional and must contain
lowercase ASCII letters, numbers, and single hyphens. Other extra request fields
are rejected. Duplicate names and slugs return `409`; invalid fields return
`422`. Missing or invalid login returns `401`; non-Admin returns `403`; an
unknown category ID on update or delete returns `404`. Deleting a category
referenced by any recipe, including drafts, returns `409 CATEGORY_IN_USE` with
the recipe count; the category and recipes remain intact. Errors use
`application/problem+json` with `type`, `title`, `status`, and `detail`.

The server creates a Vietnamese-friendly slug and adds `-2`, `-3`, etc. when
another name normalizes to the same slug. Renaming a category keeps its existing
slug unless the Admin explicitly includes a new slug in the update request. The
seed command inserts missing starter categories only, so it will not overwrite
Admin edits. The existing Category table supports these features; no new migration
is required. Use the normal role provisioning process for an Admin account;
there is no production development login or role override.

Set `JWT_SECRET` to a long random value outside development. Passwords use
PBKDF2-HMACSHA512 with 210,000 iterations; refresh tokens are stored only as SHA-256 hashes.

## Shared storage and welcome email (Issue #45)

The S3-compatible `S3FileStorage` adapter offers validated image upload,
read, and idempotent delete operations for Issue #43's image endpoints. It
accepts JPEG, PNG, WebP, and AVIF up to 5 MB and validates file signatures.
The welcome-email outbox is created during local registration and processed
by the separate `email-worker` service with three scheduled retries. Set the
MinIO and SMTP variables in `.env.example`; see
[`docs/FILE-STORAGE-JOBS.md`](../docs/FILE-STORAGE-JOBS.md) for the contract
and local verification steps.
