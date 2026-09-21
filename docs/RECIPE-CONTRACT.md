# Base Recipe Contract

This contract covers FR-RCP-003: an authenticated Author or Admin creates a recipe draft
with real database ownership.

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

## Errors

Errors use `application/problem+json` without stack traces:

- `401 AUTH_TOKEN_INVALID` or `AUTH_TOKEN_EXPIRED`
- `403 RECIPE_FORBIDDEN`
- `409 RECIPE_SLUG_EXISTS`
- `422 VALIDATION_ERROR`, with field messages in `errors`

## Deferred scope

Steps and ingredients are intentionally not accepted by this base contract. Their models,
schemas, and CRUD operations belong to FR-RCP-009 and FR-RCP-010. Search vectors and Redis
cache invalidation belong to later search/performance work.
