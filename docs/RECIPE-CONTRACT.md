# Recipe API Contract

This contract covers FR-RCP-002, FR-RCP-003, FR-RCP-004, FR-RCP-007, FR-RCP-009, and
FR-RCP-010. An authenticated Author or Admin creates a recipe draft with real database
ownership.

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

## Recipe detail

`GET /api/v1/recipes/{slug}` returns the full recipe contract: category and author
summaries, nutrition, the ordered `ingredients` list, and the ordered `steps` list,
alongside the fields already returned by create/update. A published recipe is public.
A Draft or Archived recipe is limited to its owner or an Admin; anyone else (including
anonymous callers) receives `403 RECIPE_FORBIDDEN`. An unknown slug returns
`404 RECIPE_NOT_FOUND`.

## Ingredients

The owner or an Admin can use these routes:

| Method | Path | Result |
|---|---|---|
| `POST` | `/api/v1/recipes/{id}/ingredients` | `201`, ingredient body and `Location` |
| `PUT` | `/api/v1/recipes/{id}/ingredients/{ingredientId}` | `200`, updated ingredient |
| `DELETE` | `/api/v1/recipes/{id}/ingredients/{ingredientId}` | `204` |

Create accepts `ingredientName` (trimmed, 1-120 characters), a positive `quantity`
(up to 2 decimal places), and `unit` (trimmed, 1-30 characters). An ingredient name
is looked up or created in the shared `ingredients` table, then linked to the recipe
with the next `orderIndex`. Adding the same ingredient twice returns
`409 RECIPE_INGREDIENT_EXISTS`. Update accepts the same fields and an optional
`orderIndex` (0 through the current ingredient count minus one) to move it; delete
closes the ordering gap. Unknown recipes/ingredient rows return `404`; another
Author receives `403`; invalid input returns `422`.

## Errors

Errors use `application/problem+json` without stack traces:

- `401 AUTH_TOKEN_INVALID` or `AUTH_TOKEN_EXPIRED`
- `403 RECIPE_FORBIDDEN`
- `404 RECIPE_NOT_FOUND`, `RECIPE_STEP_NOT_FOUND`, or `RECIPE_INGREDIENT_NOT_FOUND`
- `409 RECIPE_SLUG_EXISTS` or `RECIPE_INGREDIENT_EXISTS`
- `422 VALIDATION_ERROR`, with field messages in `errors`

## Deferred scope

Recipe image metadata, stored objects, search vectors, and Redis cache invalidation
belong to their assigned integration issues.
