# Project Roadmap

Keep future work here. Create four new Issues only when the current cycle is almost complete.

## Cycle 1 - Core Data And Access

| Owner | Feature group | SRS | Important dependency |
|---|---|---|---|
| Dan | Local registration and login | FR-AUTH-001, FR-AUTH-002, NFR-SEC-001 | None |
| Han | Create and update categories | FR-CAT-003, FR-CAT-004 | Start with a seeded Admin; integrate #1 later |
| Minh Anh | Category detail and simple recipe cards | FR-CAT-002 | Start with an empty recipe list; add cards after #4 |
| Hieu | Draft recipe creation and the base Recipe model | FR-RCP-003 | Start with a seeded Author; integrate #1 later |

Agent Bootstrap provides the category list foundation for FR-CAT-001. Seeded users are only temporary development data.

## Cycle 2 - Main Application Flow

| Owner | Feature group | SRS | Important dependency |
|---|---|---|---|
| Dan | Refresh token, sign out, publish, unpublish, and shared ownership checks | FR-AUTH-004, FR-AUTH-005, FR-RCP-005, NFR-SEC-002, NFR-SEC-006 | Cycle 1 authentication and Recipe model |
| Han | Create and update recipes, ingredients, cooking steps, safe category deletion, and recipe database deletion | FR-CAT-005, FR-RCP-004, FR-RCP-007, FR-RCP-009, FR-RCP-010 | Hieu's base Recipe model and Dan's ownership foundation |
| Minh Anh | View and update profiles, and show recipe details | FR-AUTH-006, FR-AUTH-007, FR-RCP-002 | Cycle 1 authentication and Recipe model |
| Hieu | Public recipe list, filters, sorting, and pagination | FR-RCP-001, FR-SRCH-002 to FR-SRCH-004 | Published recipe data from Dan's flow |

Han owns recipe update and database deletion with ownership rules. Hieu adds archive behavior and external image cleanup in Cycle 3.

## Cycle 3 - Supporting Features

| Owner | Feature group | SRS | Important dependency |
|---|---|---|---|
| Dan | Google OAuth, security, health checks, shared logging, and final integration | FR-AUTH-003, FR-OBS-001 to FR-OBS-003, NFR-SEC-003 to NFR-SEC-007, NFR-REL-001, NFR-REL-002, NFR-MAINT-001, NFR-MAINT-002 | Main application flows |
| Han | MinIO storage, welcome email job, deployment, and backup | FR-FILE-001, FR-FILE-002, FR-JOB-001, NFR-REL-003, NFR-SCALE-001, NFR-SCALE-003 | Stable auth and recipe data |
| Minh Anh | Recipe SEO, accessibility, sitemap, and final user documentation | FR-JOB-003, NFR-PERF-005, NFR-USE-001 to NFR-USE-004, NFR-MAINT-003, NFR-MAINT-004, NFR-SEO-001 to NFR-SEO-004 | Recipe detail pages |
| Hieu | Recipe archive, images, image resize job, full-text search, Redis cache, and performance checks | FR-RCP-006, FR-RCP-008, FR-JOB-002, FR-SRCH-001, NFR-PERF-001 to NFR-PERF-004, NFR-SCALE-002 | Han's MinIO service and recipe delete flow |

Every member adds useful logs and tests for their own features. Dan provides the shared logging and security foundation.
