# Recipe Detail Contract

FR-RCP-002 serves a recipe at `GET /api/v1/recipes/{slug}`. The recipe cards on
`/recipes` link to `/recipes/{slug}`, where the frontend loads this endpoint.
The 100 Lab 2 sample recipes use slugs derived from their dish names (for
example, `pho-bo-ha-noi`); re-running the seed updates existing numeric
`lab2-recipe-###` slugs in place without recreating those recipes.

## Visibility and errors

- A guest or Reader can view a Published, non-deleted recipe.
- The owner or an Admin can also view its Draft or Archived version.
- A non-owner requesting a private recipe receives `403`; an unknown slug or a
  soft-deleted recipe receives `404`. An invalid Bearer token receives `401`.
- Errors use `application/problem+json` (RFC 7807).

## Response

The `200` response includes the base recipe fields, status, nutrition and
`publishedAt`, plus `category`, `author`, `ingredients`, `steps`, and `images`.
Ingredients are ordered by `orderIndex`, steps by `stepNumber`, and images by
`orderIndex`. Each ingredient has its name, quantity, and unit; each step has
its instruction, optional duration, and optional image; each image has its
available URLs, alt text, and primary flag. Empty child collections return
empty arrays so a Draft can still be opened before its steps or ingredients
are added.

The backend eager-loads related data to avoid per-row queries. Anonymous
Published detail responses are cached in Redis for 5 minutes;
authenticated detail responses are not shared. Recipe, step, archive, and
image mutations advance the shared recipe-cache version.
