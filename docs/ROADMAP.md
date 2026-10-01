# Project Roadmap

Lab 04 moved all former Cycle 3 API work and part of Cycle 4 forward. Keep the old Issues as history; never rename or reuse them for a later cycle.

## Lab 04 - Complete API Endpoints

| Owner | Issue | Scope moved forward | Status |
|---|---:|---|---|
| Dan | #38 | Google OAuth, profile, publish, and unpublish APIs | Done |
| Han | #39 | Recipe update/delete and cooking-step APIs | Ready |
| Minh Anh | #40 | Recipe detail and ingredient APIs | Ready |
| Hieu | #43 | Archive, search, and recipe-image APIs | Ready |

## Cycle 3 - Supporting Infrastructure

| Owner | Issue | Feature group | SRS | Dependency |
|---|---:|---|---|---|
| Dan | #44 | Security, observability, and integration foundation | FR-OBS-001 to FR-OBS-003, NFR-SEC-003 to NFR-SEC-007, NFR-REL-001, NFR-REL-002, NFR-MAINT-001, NFR-MAINT-002 | #38 |
| Han | #45 | MinIO storage and welcome email job | FR-FILE-001, FR-JOB-001, NFR-SCALE-001 | Auth contract and #43 image metadata |
| Minh Anh | #46 | Accessibility, SEO, sitemap, and frontend performance | FR-JOB-003, NFR-PERF-005, NFR-USE-001 to NFR-USE-004, NFR-SEO-001 to NFR-SEO-004 | #40 |
| Hieu | #47 | Image resize, Redis cache, and performance checks | FR-JOB-002, NFR-PERF-001 to NFR-PERF-004, NFR-SCALE-002 | #43 and #45 storage contract |

All Cycle 3 Issues are new Project items in `Ready`. Finish the related Lab 04 Issue before starting dependent work.

## Cycle 4 - Release Hardening

| Owner | Remaining work |
|---|---|
| Dan | Final security audit, cross-feature integration, release checks, and review coordination |
| Han | Safe file deletion, deployment, backup, data durability, container, and proxy setup |
| Minh Anh | Final user documentation plus accessibility and SEO QA |
| Hieu | Load testing, cache/storage cleanup, and final query tuning |

Cycle 4 contains no duplicated API endpoint work from Lab 04. Create new Cycle 4 Issues only when Cycle 3 is almost complete.
