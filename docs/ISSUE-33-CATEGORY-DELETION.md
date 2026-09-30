# Issue #33: delete an empty category

Owner: Nguyễn Ngọc Hân (`Ericismee`). Reviewer: Nguyễn Ngọc Trường Dân (`0Yaam`). Source requirement: FR-CAT-005 in SRS v1.0.0, pages 26–27.

## API contract

`DELETE /api/v1/categories/{category_id}` requires a current Admin Bearer token. A successful deletion returns `204` with no body. A missing category returns `404 CATEGORY_NOT_FOUND`. A category referenced by any recipe, including a draft, returns `409 CATEGORY_IN_USE`; the RFC 7807 `detail` includes the recipe count. Missing or invalid credentials return `401`; an authenticated non-Admin receives `403`. All errors use `application/problem+json` without a stack trace.

The service checks recipe references before deleting and handles a database integrity error if a reference appears during the delete. The existing Category and Recipe foreign key supports this rule; no migration is needed. The public category list includes recipe counts in one aggregate query so the Admin page can explain why deletion is unavailable. The API remains authoritative if the count changes after the list loads.

## Admin page

Selecting a category shows a deletion section. A category with recipes displays the count and prevents the delete action. An empty category requires a second confirmation click. The page reports success, permission/session errors, `404`, and `409` in English and Vietnamese. The confirmation is reset when selection changes.

## Team integration

Category create/update from Issue #2 and the shared auth dependency are reused. Issue #34 and PR #35, owned by `0Yaam`, introduce shared repositories and Unit of Work. This change keeps the existing category service/session convention so the Issue #34 owner can integrate the shared abstraction after that PR merges. The FastAPI implementation uses its existing service functions and RFC 7807 handlers for the .NET-specific SRS terms. The current category list has no application cache; the frontend uses `no-store`. If the NFR-PERF owner adds a cache, deletion must invalidate the shared category key together with create/update.

## Verification

`backend/tests/test_categories.py` covers 204, repeated deletion 404, non-Admin 403, and 409 with draft and published recipes. The frontend production build checks the page and translation keys; the Admin page exposes the blocked, confirmation, success, and error states. Run Ruff, the full pytest suite, frontend lint, and frontend build before review.
