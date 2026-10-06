# Recipe API Contract

This contract covers FR-RCP-003, FR-RCP-004, FR-RCP-007, and FR-RCP-010.
An authenticated Author or Admin creates a recipe draft with real database ownership.

## Endpoint

`POST /api/v1/recipes` requires a Bearer access token. The request body uses camelCase:

```json
{
  "title": "Gỏi cuốn tôm thịt",
  "description": "Món gỏi cuốn kiểu Việt Nam.",
  "categoryId": "00000000-0000-0000-0000-000000000000",
  "prepTimeMinutes": 20,
  "cookTimeMinutes": 0,
  "servings": 4,
  "difficulty": 1,
  "instructions": "Chuẩn bị nguyên liệu trước khi cuốn.",
  "nutrition": {
    "calories": 210,
    "protein": 8,
    "carbohydrates": 28,
    "fat": 7,
    "fiber": 3,
    "sodium": 420
  }
}
```

Difficulty values are `1=Easy`, `2=Medium`, `3=Hard`, and `4=Expert`. Nutrition and each
nutrition value are optional. Title is 5-200 characters, description is 1-2000 characters,
prep time and servings are positive, and cook time may be zero for a no-cook recipe.

The server derives `authorId` from the validated token, generates `slug` from `title`, and
always assigns `Draft`. A successful request persists the recipe and returns `201 Created`
with a `Location` header.
The response also includes `rowVersion` and a quoted `ETag` header. Clients should
retain either value for a later update.

## Update and delete

`PUT /api/v1/recipes/{id}` replaces the editable fields in the create payload. The
caller must own the recipe or be an Admin. Supply the current quoted `ETag` in
`If-Match`, or the unquoted `rowVersion` in the JSON body. A missing version returns
`428 RECIPE_VERSION_REQUIRED`; a stale version returns `409 RECIPE_VERSION_CONFLICT`.
The response returns the next `rowVersion` and `ETag`. Changing the title preserves
the existing slug and public URL.

`DELETE /api/v1/recipes/{id}` hard-deletes the recipe and cascades to its existing
ingredient and step rows. It returns `204` with no body. Future image records and
object storage cleanup are owned by the separate image/storage integration issues.

## Cooking steps

The owner or an Admin can use these routes:

| Method | Path | Result |
|---|---|---|
| `POST` | `/api/v1/recipes/{id}/steps` | `201`, step body and `Location` |
| `PUT` | `/api/v1/recipes/{id}/steps/{stepId}` | `200`, updated step |
| `DELETE` | `/api/v1/recipes/{id}/steps/{stepId}` | `204` |

Create accepts `instruction` (trimmed, 1-2000 characters), optional positive
`durationMinutes`, and optional `imageUrl` (up to 2048 characters). The server
appends the next `stepNumber`. Update accepts the same fields and an optional
`stepNumber` from 1 through the current step count to move a step. Delete closes
the numbering gap. A step change also advances the parent recipe's `rowVersion`.
Unknown recipes/steps return `404`; another Author receives `403`; invalid input
returns `422`. Errors are RFC 7807 JSON.

## Errors

Errors use `application/problem+json` without stack traces:

- `401 AUTH_TOKEN_INVALID` or `AUTH_TOKEN_EXPIRED`
- `403 RECIPE_FORBIDDEN`
- `409 RECIPE_SLUG_EXISTS`
- `422 VALIDATION_ERROR`, with field messages in `errors`

## Deferred scope

Ingredients remain in FR-RCP-009. Recipe image metadata, stored objects, search
vectors, and Redis cache invalidation belong to their assigned integration issues.
