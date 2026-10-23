# Lab 7 profile and category directory

Owner: Ericismee. Reviewer: 0Yaam. Issue #78 includes the former scope of #82.

## Profile

The existing `/profile` screen uses the shared auth store and the authenticated
GET/PUT `/api/v1/auth/profile` contract documented in `PROFILE.md`. Editable
fields are fullName, userName and avatarUrl. Email and roles are read-only.
The issue explicitly retains editable userName; this differs from the original
SRS FR-AUTH-007 wording and follows the already merged profile contract.

Each access-token session now mounts an isolated profile form. Signing out or
switching accounts cannot leave the previous account's data visible or submit
it for the next account. Inputs are disabled during save and editing clears the
old success message. The form retains validation, duplicate-name, signed-out,
loading, unchanged, save, success, error and retry states.

The backend chooses the account from the authenticated token. A regression test
also submits another account's id/userId and verifies that account is unchanged.
Existing tests cover immutable email/role and absence of secret response fields.

## Public categories

`/categories` uses the existing `getCategories` helper and `CategoryGrid`; one
list request returns all names, descriptions, counts and stable slug links.
It has no create/update/delete controls. The route has translated metadata,
canonical URL, loading boundary and an API error boundary. Retry reloads the
server-rendered request. Empty results reuse the shared empty state.

Header/footer navigation, category detail back links and sitemap now include
the directory. Shared category cards expose list/listitem semantics and retain
their responsive grid and keyboard focus styles. No database/API contract or
new dependency is introduced.

## Checks on 22 October 2026

- Ruff: passed.
- Full backend suite: 147 passed.
- Frontend lint and production build: passed.
- Playwright against a production frontend and isolated mock API: passed for
  nine categories, stable links, canonical metadata, keyboard focus, mobile
  overflow, empty results, API failure and recovery.
- Profile browser QA: signed-out view, disabled unchanged form, save payload,
  read-only email, duplicate username, account isolation and retry passed.

The browser runner is `frontend/scripts/qa-profile-categories.cjs`. Build first,
then run it with Node and Playwright/Chromium available on NODE_PATH. It starts
its own frontend on port 3187 and a mock API on 3188, and shuts both down on
completion. `LAB7_QA_PORT` can select another adjacent pair. Mock browser QA
complements the real API tests; it is not a production deployment test.
