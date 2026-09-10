# Project Roadmap

This roadmap keeps future work in one place. Create smaller GitHub Issues only when a cycle starts.

## Cycle 1 - Core Data And Access

| Owner | Planned work | SRS |
|---|---|---|
| Dan | Local registration and login | FR-AUTH-001, FR-AUTH-002 |
| Han | Create and update categories | FR-CAT-003, FR-CAT-004 |
| Minh Anh | Category detail and simple recipe cards | FR-CAT-002 |
| Hieu | Draft recipe creation and the base Recipe model | FR-RCP-003 |

The Agent Bootstrap already provides the category list foundation for FR-CAT-001.

## Cycle 2 - Main Recipe Flow

| Owner | Planned work | SRS |
|---|---|---|
| Dan | Token refresh, sign out, publish, unpublish, and ownership checks | FR-AUTH-004, FR-AUTH-005, FR-RCP-005, NFR-SEC-002, NFR-SEC-006 |
| Han | Recipe ingredients and cooking steps | FR-RCP-009, FR-RCP-010 |
| Minh Anh | View and update user profiles | FR-AUTH-006, FR-AUTH-007 |
| Hieu | Public recipe list, detail, filters, sorting, paging, archive, and delete | FR-RCP-001, FR-RCP-002, FR-RCP-006, FR-RCP-007, FR-SRCH-002 to FR-SRCH-004 |

## Cycle 3 - Supporting Features

| Owner | Planned work | SRS |
|---|---|---|
| Dan | Google OAuth, security checks, health checks, and final integration tests | FR-AUTH-003, FR-OBS-001 to FR-OBS-003, NFR-SEC-001, NFR-SEC-003 to NFR-SEC-007, NFR-MAINT-001, NFR-MAINT-002, NFR-REL-001, NFR-REL-002 |
| Han | Safe category deletion, MinIO storage, background jobs, deployment, and backup | FR-CAT-005, FR-FILE-001, FR-FILE-002, FR-JOB-001 to FR-JOB-003, NFR-REL-003, NFR-SCALE-001, NFR-SCALE-003 |
| Minh Anh | Recipe SEO, accessibility, frontend quality, and final user documentation | NFR-PERF-005, NFR-USE-001 to NFR-USE-004, NFR-MAINT-003, NFR-MAINT-004, NFR-SEO-001 to NFR-SEO-004 |
| Hieu | Recipe images, Redis cache, full-text search, and performance checks | FR-RCP-008, FR-SRCH-001, NFR-PERF-001 to NFR-PERF-004, NFR-SCALE-002 |

## Shared Product Rules

- Public users see only Published recipes.
- Authors can change only their own recipes. Admins have the wider access defined by the SRS.
- A recipe needs at least one ingredient and one step before publication.
- Uploaded images must match their real file type and must not be larger than 5 MB.
- The API uses `/api/v1` and RFC 7807 error responses.
- PostgreSQL stores business data. Redis is a cache, not the source of truth.
