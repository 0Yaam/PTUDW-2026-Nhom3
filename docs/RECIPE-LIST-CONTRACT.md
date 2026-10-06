# Recipe List Contract

FR-RCP-001, FR-SRCH-002, FR-SRCH-003, and FR-SRCH-004 expose the public recipe
collection at `GET /api/v1/recipes`.

## Query parameters

| Parameter | Default | Rule |
| --- | --- | --- |
| `page` | `1` | integer greater than or equal to 1 |
| `pageSize` | `12` | integer from 1 through 50 |
| `categoryId` | omitted | valid UUID; an unknown category returns an empty list |
| `difficulty` | omitted | `Easy`, `Medium`, `Hard`, or `Expert` |
| `maxCookTime` | omitted | non-negative integer minutes |
| `minServings` | omitted | positive integer |
| `sort` | `-createdAt` | `createdAt`, `-createdAt`, `title`, `-title`, `cookTime`, or `-cookTime` |

All supplied filters are combined with AND. A leading `-` sorts descending.

## Visibility

- Guest and Reader: published recipes only.
- Author: all published recipes, plus that Author's own Draft and Archived recipes.
- Admin: every non-deleted recipe.

Rows marked `is_deleted` are never returned. A malformed Bearer token returns the normal
RFC 7807 `401` response; omitting the token is a valid public request.

## Response

```json
{
  "items": [],
  "totalCount": 0,
  "page": 1,
  "pageSize": 12,
  "totalPages": 0,
  "hasNextPage": false,
  "hasPreviousPage": false
}
```

Every item includes its identifier, title, slug, description, category summary, prep/cook
minutes, servings, numeric difficulty, status, and creation time. Invalid query values return
`422 application/problem+json`; a valid query with no matching rows returns `200` and an empty
`items` list.

## Cache

Anonymous requests are cached in the API process for 15 minutes under the exact
`{path}?{queryString}` key required by the SRS. Authenticated requests intentionally bypass that
shared cache because their result can contain user- or role-specific private recipes. A future
publish/archive/delete flow clears this cache when it changes public recipe visibility.

## Issue #43: search, archive, and images

`GET /api/v1/recipes/search?q=...` is always public. It returns the same paged
shape and accepts the list filters, sort, and pagination parameters above.
`q` is required (2–100 characters); search terms are combined with AND. The
default sort is relevance, with title weighted above description, then newest
first. Each result adds `relevanceScore`; an explicit list `sort` overrides
relevance ordering. Search never exposes Draft,
Archived, or soft-deleted recipes, including when a Bearer token is supplied.
PostgreSQL stores an `unaccent`-normalized `tsvector`, maintained on recipe
insert and title/description updates, and indexes it with GIN. An empty match
returns `200` with `items: []`; invalid parameters return RFC 7807 `422`.

`PATCH /api/v1/recipes/{id}/archive` requires the owner or Admin. It changes
status to `Archived`, returns the recipe and ETag, and invalidates the public
list cache. Repeating the request is safe; archived recipes cannot be published
through the existing publish endpoint.

`POST /api/v1/recipes/{id}/images` accepts multipart field `file`, validates
JPEG, PNG, WebP, or AVIF MIME and signature, and rejects empty or >5 MB files.
The image is stored in MinIO under `recipes/{id}` and its metadata is persisted
in `recipe_images`. The first image is primary. The response includes `id`,
`recipeId`, `originalUrl`, nullable `mediumUrl`/`thumbnailUrl`/`altText`,
`isPrimary`, and `orderIndex`. Image processing/resizing is not part of this
issue, so the derivative URLs remain null.

`PATCH /api/v1/recipes/{id}/images/{imageId}` with
`{"isPrimary": true}` makes an image primary. The SRS path ending in `/primary`
is also accepted as a compatibility alias. `DELETE` on the image resource
removes its stored object and metadata; when the deleted image was primary,
the next image becomes primary. All image mutations require owner/Admin.
Invalid files return RFC 7807 `400`, absent resources `404`, forbidden `403`,
and unavailable object storage `503`.
