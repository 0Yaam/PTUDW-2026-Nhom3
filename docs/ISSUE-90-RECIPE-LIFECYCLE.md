# Issue #90 - Recipe authoring lifecycle

Owner: ThanhXuanHieu. Reviewer: 0Yaam.

SRS: FR-RCP-003 through FR-RCP-007, FR-RCP-009, FR-RCP-010.
Verification date: 2026-11-03 (Asia/Saigon).

## Implementation

1. Reuse `RecipeDraftForm` for `/recipes/new` and `/recipes/{slug}/edit`.
   Creation saves a Draft, then opens the existing form in edit mode.
2. Load detail and the current profile before editing. The detail page exposes
   an edit link to the owner/Admin. Backend permissions remain authoritative.
3. Save base fields with the loaded `rowVersion` in `If-Match`. Keep inputs on
   validation, permission, network, and concurrency errors. Reload asks before
   discarding unsaved input. A pending operation prevents duplicate clicks.
4. Manage ingredient and step rows through existing POST/PUT/DELETE routes.
   Each row has explicit save and move up/down controls. Save base fields before
   changing rows, and save all rows before lifecycle actions. A failed refresh
   or an unknown row-save result blocks further writes until explicit reload.
5. Reuse publish/unpublish/archive/delete. Publish requires an ingredient and a
   step, as enforced by the existing backend contract. Archived has no restore
   endpoint. Archive/delete require confirmation. The UI explains public visibility.
6. Refresh detail and Next router data after successful writes. Existing Redis
   invalidation handles public list/detail/search. Delete cancels resize jobs and
   queues image object cleanup in the same transaction as metadata deletion.

No new REST endpoints, database migrations, dependencies, global CSS, or shared
layout changes were introduced. New styles use the existing recipe CSS Modules.
Translations extend the recipe namespace in both Vietnamese and English.

## Integration gaps fixed

- Recipe authentication previously checked only JWT signature/expiry/user ID.
  After the password-management merge, Auth also validates `sessionVersion`.
  Recipe dependencies now reuse `read_access_token` and compare the database
  session version. A revoked session cannot read private recipes or mutate them.
  Auth source files were not edited for this issue.
- Deleting a recipe now explicitly cancels resize jobs. PostgreSQL already has
  a cascading foreign key; explicit cancellation also prevents orphan jobs in
  SQLite tests, where foreign-key cascading is not enabled by default.
- UI testing reproduced duplicate form rendering after reload because sibling
  form/content components used the same React key. The form no longer uses that
  duplicate key. Only the content rows remount after confirmed reload.

## Automated evidence

Commands run from the repository root:

```powershell
uv sync --directory backend
uv run --directory backend ruff check .
uv run --directory backend pytest --cov=culinary_blog_api -q --tb=short --show-capture=no
npm ci --prefix frontend
npm run lint --prefix frontend
npm run build --prefix frontend
.\start-all.ps1
```

- Backend Ruff: passed.
- Backend pytest after session-revocation fix: **162 passed, 89% coverage**.
- New lifecycle tests: full owner journey, anonymous/other Author denial across
  recipe/ingredient/step writes, Admin acting without taking ownership, and
  password-change revocation across recipe reads/writes.
- Frontend lint and production build passed. The final container build also
  compiles the new edit route. No package version or lockfile changes.
- Docker Compose started PostgreSQL, Redis, MinIO, API, frontend, email/file/image
  workers. The API startup ran migration upgrade and the existing seed command.

## Manual evidence on PostgreSQL/Redis

Using the user's test Admin session and a dedicated `QA Lifecycle 20261103`
recipe (slug `qa-lifecycle-20261103`):

- Created Draft in UI, reopened edit with real fields/category/owner.
- Added Rice (2 cups), added two cooking steps, moved step 2 to position 1.
- A short title showed field validation and kept description/rows intact.
- Updated title without changing the slug.
- Published in UI: anonymous detail 200; list/search contained the recipe and
  subsequent requests were Redis HIT.
- Returned to Draft in UI: anonymous detail 403 `RECIPE_FORBIDDEN`; previously
  cached list/search returned MISS and excluded the recipe.
- Simulated a concurrent edit on this QA recipe only: saving the older form
  returned 409 and preserved the unsaved title; explicit reload showed the saved
  data. No seed recipe was changed by these test actions.

The user personally confirmed archive/delete in the UI. API logs recorded archive
200 and delete 204. PostgreSQL checks afterward found no QA recipe or its child
ingredient/step/image rows. The old detail URL returned 404, search returned zero
results, and 101 original recipes remained. No disposable account was created;
the user signed into their existing test Admin account.

Desktop 1366px and mobile 390px checks showed no horizontal overflow. Changing
VI/EN retained recipe values. After the React-key correction, explicit reload
left exactly one title input/form. The final Docker frontend build passed.
Readiness reported database/Redis/MinIO Healthy and Alembic was at
`20261024_0011 (head)`.

## Review and known limits

- `npm audit` reports 21 inherited dependency advisories: 16 moderate, 4 high,
  1 critical (including Next). Dependency upgrades require a separate reviewed
  change; no automatic `npm audit fix` was run in this issue.
- Ingredient/step saves are individual transactions. The form explains this;
  it does not claim that several row edits save atomically together.
- No refresh/retry can guarantee a save result after a lost response. The UI
  retains input and requires reloading persisted data before another row write.
- The branch integrated `origin/main` using `--no-commit`. The merge is pending
  user review; HEAD was not advanced and no commit or push was performed.
- The six pre-existing modified files and untracked reports/attachments were
  retained. A stash named `before-recipe-lifecycle-main-integration-20261103`
  remains available as the pre-integration backup.

Issue work relative to `origin/main` is confined to recipe dependencies/service,
the lifecycle test, recipe form/content/detail components and CSS Modules,
the edit page, recipe API client, recipe translations and recipe documentation.
Other differences in `git status` include the approved main integration and the
pre-existing local work; they are not all newly authored by this issue.
