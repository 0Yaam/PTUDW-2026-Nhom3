# Profile

This page covers FR-AUTH-006 and FR-AUTH-007: a signed-in user reads and updates
their own account.

## Endpoints

Both live on the auth router and both require a Bearer access token. Neither
takes a user id: the token decides whose profile is touched, so there is no id
in the path for a caller to swap for somebody else's.

`GET /api/v1/auth/profile` returns the signed-in account.

```json
{
  "id": "5b73c29e-3fab-43d1-9fec-093d149298ed",
  "fullName": "Nguyễn Minh Anh",
  "email": "minhanh@example.com",
  "userName": "minhanh_bep",
  "avatarUrl": "https://example.com/a.png",
  "roles": ["Author"]
}
```

`PUT /api/v1/auth/profile` replaces the editable fields and returns the same
shape. The form always sends all three, so this is a replacement rather than a
patch.

```json
{
  "fullName": "Nguyễn Minh Anh",
  "userName": "minhanh_bep",
  "avatarUrl": "https://example.com/a.png"
}
```

The response is the existing `UserRead` schema, the same one login and register
already return. It has no `password_hash`, no `access_failed_count` and no
`lockout_until`, so those cannot leak through this route by accident. A test
asserts their absence rather than trusting the schema to stay correct.

## What may be changed

| Field | Editable | Why |
|---|---|---|
| `fullName` | yes | 1 to 150 characters, trimmed |
| `userName` | yes | 3 to 50 letters, numbers or underscores; unique across accounts |
| `avatarUrl` | yes | must start with `http://` or `https://`, up to 500 characters; blank clears it |
| `email` | no | it is the login identifier, so changing it needs a re-verification flow |
| `roles` | no | privilege belongs to an admin, never to the account itself |

Extra fields in the request body are ignored, so sending `email` or `roles`
changes nothing. Two tests cover that.

`fullName` and `userName` are checked by `clean_full_name` and `clean_user_name`
in `auth/schemas.py`, the same functions registration uses, so the two paths
cannot drift apart.

## Errors

Invalid fields return `422 VALIDATION_ERROR` through the shared handler, as an
RFC 7807 problem with one entry per field:

```json
{
  "type": "VALIDATION_ERROR",
  "title": "Validation Error",
  "status": 422,
  "detail": "One or more fields are invalid.",
  "errors": {
    "fullName": ["Value error, Full name is required"],
    "userName": ["Value error, User name may contain only letters, numbers, and underscores"],
    "avatarUrl": ["Value error, Avatar URL must start with http:// or https://"]
  }
}
```

A user name another account owns returns `409 USER_NAME_TAKEN`. The service
checks first for a clear message and also catches `IntegrityError`, because
between the check and the commit another request may claim the same name; the
unique index is what actually decides.

No token, a malformed token, or a token for an account that has since been
deleted all return `401 UNAUTHORIZED`. The deleted case is already handled by
`get_current_user`, which loads the account on every request.

## Page states

`/profile` is a client component, because the access token lives in
`sessionStorage`.

| State | What the user sees |
|---|---|
| Checking session | "Checking your session…" while the token is read and refreshed |
| Signed out | A panel explaining the page is private, with a link to sign in |
| Loading | "Loading your profile…" while the API answers |
| Loaded | The form, filled from the API, with Save disabled until something changes |
| Saved | A confirmation banner in an `aria-live` region |
| Field invalid | A message under each field, `aria-describedby` linked to its input |
| Name taken | The 409 message shown under the user name field |
| API unreachable | "The API did not answer. Nothing was changed on your account." and a Try again button |
| Session expired | The session is cleared and the sign-in panel returns |

Email is rendered as a read-only input with a note saying why, rather than
hidden, so a user can still confirm which account they are editing.

The avatar uses a plain `<img>`. `next/image` needs every remote host listed in
`next.config`, and an avatar may be hosted anywhere. When FR-FILE-001 brings
MinIO uploads in Cycle 4, the host becomes known and this can move to
`next/image`.
