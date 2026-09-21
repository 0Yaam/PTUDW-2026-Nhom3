# Culinary Blog API

This folder contains the FastAPI backend. Use the root [README](../README.md) for setup and test commands.

The API includes categories plus local registration and login under `/api/v1/auth`.

## Category management (Issue #2; FR-CAT-003/004)

The public `GET /api/v1/categories` lists categories. Admin requests use the
`accessToken` returned by `POST /api/v1/auth/login` as `Authorization: Bearer <token>`.
The backend verifies the signature and reads the user's current role from the
database. Registration creates an Author; it does not grant Admin rights.

| Action | Request body | Success |
| --- | --- | --- |
| `POST /api/v1/categories` | `{ "name": "Món Việt", "description": "..." }` | `201`, Category object, `Location: /api/v1/categories/{slug}` |
| `PUT /api/v1/categories/{id}` | `{ "name": "Tên mới", "description": null, "slug": "ten-moi" }` | `200`, updated Category object |

`name` is trimmed, 2–50 characters, and cannot contain HTML. `description` is
optional and cannot contain HTML. On update, `slug` is optional and must contain
lowercase ASCII letters, numbers, and single hyphens. Other extra request fields
are rejected. Duplicate names and slugs return `409`; invalid fields return
`422`. Missing or invalid login returns `401`; non-Admin returns `403`; an
unknown category ID on update returns `404`. Errors use
`application/problem+json` with `type`, `title`, `status`, and `detail`.

The server creates a Vietnamese-friendly slug and adds `-2`, `-3`, etc. when
another name normalizes to the same slug. Renaming a category keeps its existing
slug unless the Admin explicitly includes a new slug in the update request. The
seed command inserts missing starter categories only, so it will not overwrite
Admin edits. The existing Category table supports this feature; no new migration
is required. Use the normal role provisioning process for an Admin account;
there is no production development login or role override.

Set `JWT_SECRET` to a long random value outside development. Passwords use
PBKDF2-HMACSHA512 with 210,000 iterations; refresh tokens are stored only as SHA-256 hashes.
