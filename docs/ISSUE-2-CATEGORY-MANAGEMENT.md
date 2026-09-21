# Issue #2 — Category management handoff

Owner: Han (`Meranh05`). Reviewer: Dan (`0Yaam`). Scope: FR-CAT-003 and
FR-CAT-004 from `SRS_Culinary_Blog_v1.0.0.pdf`, pages 25–26.

## Branch and integration order

1. Work from the current `main` on the category delivery branch
   (`Eric/category-admin-i18n`).
   The older `Meranh05-patch-1` to `patch-4` branches concern README/student
   details and are not prerequisites for category management.
2. Issue #1 authentication has already been integrated into `main`. Category
   writes now use its login token and check the current database role.
3. Ask Dan to review the issue branch, then merge it into `main`. Do not merge
   the future category deletion work (FR-CAT-005) into this issue.
4. Minh Anh's category detail issue (#3) may later implement the GET route
   addressed by the new category `Location` header. This issue only owns writes
   and the existing list route.

## Implementation notes

- `POST /api/v1/categories` creates a category with a server-generated unique
  Vietnamese-friendly slug. Same-name conflicts return 409; different names
  that normalize to one slug receive `-2`, `-3`, etc.
- `PUT /api/v1/categories/{id}` changes name and description while preserving
  the existing slug when `slug` is omitted. An Admin may explicitly send a
  lowercase URL-safe `slug` to change the public URL; duplicate slugs return
  409 and invalid slugs return 422. Both routes require a valid Admin account
  in the database.
- The existing Category model already has unique name and slug columns, so no
  schema migration is part of this issue. The seed inserts missing defaults and
  leaves Admin changes alone.
- `/admin/categories` is the management page. It uses the existing app colors,
  signs in through Issue #1's endpoint, and keeps the access token only in page
  memory. The backend remains responsible for authorization.
- Public category reads bypass the previous one-hour cache so an edit appears
  on the next request. This change affects the shared list fetch and should be
  called out during review.

## Checks for the reviewer

Run `uv run --directory backend ruff check .`,
`uv run --directory backend pytest --cov=culinary_blog_api`,
`npm run lint --prefix frontend`, and `npm run build --prefix frontend`.
Manual flow: sign in as an existing Admin at `/admin/categories`, create a
category, update its name, confirm its slug stays the same, explicitly change
its slug, then try a duplicate
name. An Author account should see access denied, and the backend should reject
its direct POST and PUT requests with 403.
