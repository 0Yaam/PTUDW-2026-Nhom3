# Frontend layout review

Review of the existing interface against the layout/responsive issue. No API,
database, global CSS selector, or unrelated page styling was changed.

## Route and state audit

- The root layout supplies locale/messages only. Public routes share one site
  header and footer through `(site)/layout.tsx`; admin keeps its separate shell.
- Checked `/`, `/categories/beef`, `/recipes`, `/recipes/bo-kho`,
  `/recipes/new`, `/profile`, and `/admin/categories` in the running app at
  desktop (~1280 px) and narrow (~470 px) viewports. The visible shells and
  content did not overlap or duplicate.
- Checked the signed-out states for create recipe, profile, and admin. The
  authenticated forms/dashboard were not exercised without test credentials.
- Checked recipe-list loading, 100-result, and no-match states; recipe-detail
  loading and missing-recipe states; and a missing category.
- Added a localized, responsive root 404 page for unknown routes. It returns
  HTTP 404 and gives links back to the home page and recipe list. This page is
  standalone because an unknown route does not belong to the site or admin
  route group.

## Issues corrected during the review

- Two top-level `recipeDetail` objects in each message file caused the later,
  incomplete object to replace the full translation set. Consolidated each
  locale into one object, preserving the detail-view copy and the unique keys
  from the second object.
- Blank numeric recipe-list filters were converted to zero, producing an
  invalid default request. Blank values are now omitted from the query.
- On this Windows setup, the default Next.js Turbopack production build failed
  while spawning its worker process before these edits. The build script now
  selects Next.js's supported webpack builder; this does not affect `dev`.

## Verification

`npm run lint --prefix frontend` and `npm run build --prefix frontend` passed.
The build completed TypeScript and generated all 10 static/dynamic routes.
Manual checks used the local frontend at port 3001 and the running API at port
8000. No production deployment or authenticated admin flow was tested.
