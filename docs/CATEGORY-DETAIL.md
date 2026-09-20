# Category Detail

This page covers FR-CAT-002: a reader opens one category by its stable slug and
sees the recipes published in it.

## Endpoint

`GET /api/v1/categories/{slug}` needs no authentication.

```json
{
  "id": "b7e15073-261c-42d9-8940-a3d33abce99c",
  "name": "Vietnamese Food",
  "slug": "vietnamese-food",
  "description": "Home recipes from across Vietnam.",
  "image_url": null,
  "recipe_count": 2,
  "recipes": [
    {
      "id": "ddefe574-4f53-4795-903e-2a405d1f0023",
      "title": "Gỏi cuốn tôm thịt",
      "slug": "goi-cuon-tom-thit",
      "description": "Cuốn tươi chấm mắm nêm.",
      "prep_time_minutes": 20,
      "cook_time_minutes": 0,
      "servings": 4,
      "difficulty": 1
    }
  ]
}
```

The response repeats the `CategoryRead` fields, so the category list and the
category detail can never disagree. Field names stay snake_case to match the
existing category endpoints. Note that the auth and recipe endpoints use
camelCase instead; the team should agree on one style before the API grows.

`difficulty` uses the values from [RECIPE-CONTRACT.md](RECIPE-CONTRACT.md):
`1=Easy`, `2=Medium`, `3=Hard`, `4=Expert`.

## What a reader may see

Only recipes with status `Published` that are not soft deleted. A draft belongs
to its author, and this endpoint has no authentication, so a draft must never
appear here. `recipe_count` counts the same visible recipes.

Publishing arrives with FR-RCP-005 in Cycle 2. Until then every recipe is a
draft, so a seeded database shows the empty state. That is the correct result,
not a bug.

## Errors

An unknown slug returns `404 CATEGORY_NOT_FOUND` as an RFC 7807 problem:

```json
{
  "type": "CATEGORY_NOT_FOUND",
  "title": "Not Found",
  "status": 404,
  "detail": "Category was not found."
}
```

## Page states

| State | What the reader sees |
|---|---|
| Loading | The shared skeleton in `app/loading.tsx` |
| Found | Category information and the recipe cards |
| Empty | "No recipes here yet." inside the category page |
| Not found | A translated not-found panel with a link back to the categories |
| Error | The shared boundary in `app/error.tsx` |

The not-found state is rendered by the page itself rather than by a
`not-found.tsx` boundary. Next renders that boundary outside the next-intl
request scope, so its translated text never reached the server-rendered HTML.
One known limit remains: the HTTP status for an unknown slug is 200, not 404.
A crawler may treat it as a soft 404. This belongs with the SEO work in Cycle 3
(NFR-SEO-001 to NFR-SEO-004).
