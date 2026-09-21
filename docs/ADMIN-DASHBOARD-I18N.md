# Category Admin dashboard and i18n

## Template decision

The Admin workspace adapts the layout language of [TailAdmin Free Next.js](https://github.com/TailAdmin/free-nextjs-admin-dashboard), pinned for audit at commit `4fba02489c93171220c13cd2b44cc0161ff6d2a1`. TailAdmin is MIT licensed; its notice is preserved in `frontend/third-party/TAILADMIN-LICENSE.md`. The audited source is downloaded to the ignored `.template-audit/tailadmin` directory.

Only the useful dashboard patterns were adapted: sidebar, top bar, summary cards, responsive table, form panel, and sign-in shell. No ecommerce data, chart library, calendar, profile, TailAdmin media, authentication demo, analytics, or scripts were imported. No chart, drag-and-drop, map, or UI package from the template was added. This keeps the shared frontend small and leaves future SRS modules to their owners.

## Authorization boundary

The browser treats the dashboard as presentation. Sign-in calls `/api/v1/auth/login`; the screen opens only when the response contains the `Admin` role. Every `POST /api/v1/categories` and `PUT /api/v1/categories/{id}` also sends the Bearer token. The FastAPI `require_admin` dependency loads the current user from the database and returns 401/403 when appropriate, so hiding the dashboard is not the security boundary. The token remains in component memory and is cleared on sign-out, 401, or 403.

The sidebar links only to category management and the public site. Other SRS modules are not rendered as fake or disabled pages. Teammates can add a route and then add its authorized navigation item without changing the category form.

## English and Vietnamese

`next-intl` loads `frontend/messages/en.json` or `frontend/messages/vi.json`. The language switch stores `NEXT_LOCALE` in a first-party cookie and refreshes the current route, so existing `/` and `/admin/categories` links remain stable. UI copy, form labels, state messages, and known RFC 7807 category errors are translated. Category names and descriptions are user content and remain exactly as stored in PostgreSQL.

## FR-CAT-003 / FR-CAT-004 trace

| Requirement | Implementation |
| --- | --- |
| Admin-only create/update | `require_admin` on POST and PUT; dashboard sends the JWT. |
| Name 2–50 characters, no HTML | Pydantic validation in `categories/schemas.py`, plus matching HTML constraints. |
| Unique name | Case-insensitive service check and database unique constraint; 409 Problem Details. |
| Vietnamese slug and suffix | `slugify` removes Vietnamese marks and retries `-2`, `-3`, etc.; tested. |
| Stable slug on rename | Update changes name/description only; tested. |
| 201 + Location / 200 | Router sets status and Location; tests cover create and update. |
| 401/403/404/409/422 | Backend route/service tests cover permission and error cases. |
| Cache invalidation | The current FastAPI category list deliberately uses no application cache, and the frontend requests it with `no-store`, so there is no stale `categories:all` entry to invalidate. Shared caching is assigned to NFR-PERF in `docs/SRS-MAP.md`; when that owner adds a cache, create/update must invalidate the shared key in that same integration. |

The SRS mentions MediatR, Unit of Work, and IMemoryCache, which are .NET implementation names. This repository uses FastAPI, SQLAlchemy, service functions, and Pydantic. The observable HTTP behavior and business rules are implemented without adding a parallel .NET architecture.
