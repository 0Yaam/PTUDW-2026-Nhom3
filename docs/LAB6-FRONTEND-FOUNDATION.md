# Lab 6 frontend foundation

The blog frontend now has a shared foundation for the Lab 6 requirements.

## Completed pieces

- `frontend/src/lib/api/client.ts` centralizes the API base URL, JSON requests,
  HTTP status and RFC 7807 Problem Details errors.
- `frontend/src/lib/auth-store.ts` exposes the current session through
  `useSyncExternalStore`; login, refresh and logout updates are delivered to
  every client screen through the existing session event.
- Tailwind CSS 4 and CSS Modules are declared in `frontend/package.json` and
  share the tokens in `frontend/src/styles/tokens.css`.
- `frontend/src/components/ui/feedback.tsx` provides loading, error and empty
  states. The root error boundary uses the shared error state.
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
