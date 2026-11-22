# Culinary Blog Web App

This folder contains the Next.js App Router frontend. Use the root [README](../README.md) for setup and test commands.

The default setup starts the complete Docker system on port `3000`. To monitor
frontend edits with hot reload, run an additional dev server on port `3001`:

```powershell
.\start-all.ps1
npm run dev --prefix frontend
```

Run these commands from the repository root. Install dependencies first with
`npm ci --prefix frontend` when `node_modules` is missing or the lockfile changes.

The Agent Bootstrap includes a category page with loading, empty, and error states.

The shared visual design follows Han's selected food website reference with
project-owned imagery, a responsive theme, and reusable page sections. See
[the theme notes](../docs/UI-THEME-FOOD-WEBSITE.md) for provenance, SRS fit,
and integration boundaries.

The category Admin workspace uses a TailAdmin-inspired SaaS dashboard and
supports English/Vietnamese UI text through `next-intl`. See
[the Admin and i18n notes](../docs/ADMIN-DASHBOARD-I18N.md) for the license,
authorization boundary, teammate integration rules, and FR-CAT trace.

The public header shows a Guest badge before sign-in. Its Manage categories
links on desktop, mobile, and in the footer appear after the profile API
confirms the current session has the Admin role. The public navigation follows
session changes when users sign in or sign out on the homepage.

Issues #2 and #33 add `/admin/categories`. Sign in with an existing Admin account,
then create categories or select one to edit its name and description. An empty
category can be deleted after a second confirmation. A category with recipes
shows its recipe count and cannot be deleted; the API also rejects deletion if
recipes were added after the page loaded. The page shows validation, permission,
network, loading, empty, save, deletion, and error states. Its
access token stays in page memory and is cleared on sign-out or an unauthorized
save; a reload requires sign-in again. The API checks Admin permission for every
write. Category reads use `cache: "no-store"` so an Admin
edit or deletion appears on the next public request.

To test locally with the default Compose database, register on the homepage
first. Registration creates an Author. For **local development only**, a team
member with access to the development database can assign the Admin role to
that specific account:

```powershell
docker compose exec -T postgres psql -U culinary -d culinary_blog -c "UPDATE users SET role='Admin' WHERE email='your-email@example.com';"
```

Check for `UPDATE 1`, then sign in at `/admin/categories`. Use your configured
PostgreSQL user/database values if they differ from Compose defaults. This is
manual local setup; the application has no role-granting endpoint or production
development helper.

## End-to-end tests

Playwright tests in `e2e/` drive the Docker stack in the installed Chrome:
guest browsing and accent-free search (desktop and mobile), registration and
sign-in, an Author saving a private Draft, and the Vietnamese Admin workspace
(category creation, user search, non-Admin refusal).

```bash
.\start-all.ps1
npm run test:e2e --prefix frontend
```

Set `E2E_BASE_URL` / `E2E_API_URL` when the stack uses other ports. The run
promotes a fresh test account to Admin through `docker compose exec postgres`
and clears `ratelimit:*` counters in Redis before signed-in tests, because one
machine quickly reaches the 10 `/auth` requests per minute limit.
After the run, the global teardown executes `docker compose exec api seed`, which
removes the test accounts, categories and draft recipes again (set
`E2E_KEEP_TEST_DATA=1` to keep them for debugging).
