# Lab 6 frontend foundation

The blog frontend now has a shared foundation for the Lab 6 requirements.

## Completed pieces

- `frontend/src/lib/api/client.ts` centralizes the API base URL, JSON requests,
  HTTP status and RFC 7807 Problem Details errors for every API module.
- `frontend/src/lib/auth-store.ts` exposes the current session through
  `useSyncExternalStore`; it deduplicates initial token refresh and delivers
  login, refresh and logout updates to profile and recipe screens.
- Tailwind CSS 4 and CSS Modules are declared in `frontend/package.json` and
  share the tokens in `frontend/src/styles/tokens.css`.
- `frontend/src/components/ui/feedback.tsx` provides loading, error and empty
  states with accessible roles (`role="alert"`, `role="status"`), `aria-live`,
  and optional retry actions. These are reused across the root error boundary,
  recipe list, recipe detail, and category views.
- `frontend/src/components/site-header.tsx`, `mobile-nav.tsx`, and `site-footer.tsx`
  unify desktop/mobile navigation via Next.js `Link`, with `LocaleSwitcher`
  providing explicit `aria-label` and `aria-pressed` states.
- Pagination remains inline in `frontend/src/components/recipe-list.tsx` because
  recipe listing is the single paginated surface in the application (categories
  and admin tables are single-page views). Disabled states correctly reflect
  `hasPreviousPage`, `hasNextPage`, and loading status without duplicating logic.
- The existing site layout composes the shared header and footer around every
  public blog route. The static home, category, recipe list, recipe detail,
  profile and draft screens are kept as route-level pages with responsive
  states.
## Verification

Run these commands from the repository root:

```text
npm run lint --prefix frontend
npm run build --prefix frontend
```
