# Project Roadmap

GitHub Project is the source of current status. Future work stays as compact Backlog items until the team is ready to create detailed Issues.

Size is a rough guide: S = 1, M = 2, L = 3. Each feature owner completes all needed layers. Dan has less feature coding because he leads, reviews, and integrates. Minh Anh has lower-risk work at about 70-80% of normal effort.

## Cycle 1 - Core Data And Access

| Owner | Feature | Size | SRS | Start | Finish integration |
|---|---|---:|---|---|---|
| Dan | Local registration and login | L | FR-AUTH-001, FR-AUTH-002, NFR-SEC-001 | No dependency | Shared User model and auth contract are merged |
| Han | Create and update categories | M | FR-CAT-003, FR-CAT-004 | Existing Category model; development Admin fixture is allowed | Issue #1 auth and Admin permission checks are merged |
| Minh Anh | Category detail and simple recipe cards | M | FR-CAT-002 | Existing category seed; use an empty recipe list | Issue #4 Recipe contract is merged for real cards |
| Hieu | Base Recipe model and draft recipe creation | L | FR-RCP-003 | Agreed API/error rules; development Author fixture is allowed | Issue #1 User model and Author permission checks are merged |

Only these four feature Issues begin in Ready. Fixtures or mock identities must work only in development and tests; they never bypass production authentication.

## Cycle 2 - Main Application Flow

| Owner | Feature bundle | Size | Main dependency |
|---|---|---:|---|
| Dan | Refresh token, sign out, publish/unpublish, shared ownership checks | L | Cycle 1 auth and Recipe model |
| Han | Recipe editing, ingredients, cooking steps, and recipe deletion | L | Recipe model and Dan's ownership checks |
| Minh Anh | User profiles and recipe detail | M | Auth and Recipe model |
| Hieu | Public recipe list, filters, sorting, pagination, and archive | L | Published recipe data and agreed query contract |

Dan owns shared authentication, ownership checks, and security rules. Han reuses them for recipe changes and deletion. Hieu owns archive behavior.

## Cycle 3 - Services And Quality

| Owner | Feature bundle | Size | Main dependency |
|---|---|---:|---|
| Dan | Google OAuth, shared logging/security, health checks, final integration | M | Stable main flows |
| Han | MinIO foundation, safe category/file deletion, welcome email, deployment/backup | L | Stable auth, recipes, and deployment access |
| Minh Anh | SEO, accessibility, sitemap, short user documentation | M | Stable public pages |
| Hieu | Recipe images, resize/cleanup jobs, search, cache, performance | L | Han's MinIO foundation and recipe flows |

Cycle 3 task counts are not effort counts. Han owns shared MinIO and deployment rules. Hieu reuses MinIO for image work. Hieu's image/search bundle must be split into small linked Pull Requests. If image work blocks search, move search or cache to Dan during cycle planning; do not move SRS ownership silently.

## Main Dependency Order

1. Merge Issue #1 User/auth contracts and Issue #4 Recipe contracts early.
2. Integrate Issue #2 permissions with auth and Issue #3 cards with Recipe data.
3. Merge shared ownership checks before recipe edit, delete, publish, or archive flows.
4. Merge MinIO foundation before image upload, resize, or cleanup.
5. Stabilize public recipe pages before SEO, sitemap, search, cache, and performance checks.
