# Team Guide

## Team Members

| Name | Student ID | GitHub | Role |
|---|---:|---|---|
| Nguyen Ngoc Truong Dan | 2312590 | `0Yaam` | Team leader |
| Nguyen Ngoc Han | 2312607 | `Meranh05` | Member |
| Nguyen Minh Anh | 2312571 | `MinhAnhhhhhh` | Member |
| Tran Xuan Hieu | 2312617 | `ThanhXuanHieu` | Member |

Each owner completes the database, API, UI, useful logs, and tests for a feature when those layers apply.

## Current Cycle

Cycle 1 has four open Issues. All members can start now.

| Issue | Owner | Work | Start note |
|---:|---|---|---|
| #1 | Dan | Local registration and login | No dependency |
| #2 | Han | Create and update categories | Use a seeded Admin until #1 is ready |
| #3 | Minh Anh | Category detail and simple recipe cards | Start with an empty recipe list; add cards after #4 |
| #4 | Hieu | Draft recipe creation and the base Recipe model | Use a seeded Author until #1 is ready |

The seeded users are temporary development data. Replace them with real authentication during integration.

## High-Level Work Split

| Cycle | Dan | Han | Minh Anh | Hieu |
|---|---|---|---|---|
| 1 | Registration and login | Category create and update | Category detail and recipe cards | Draft recipe and base model |
| 2 | Tokens, publication, and ownership checks | Recipe create/update, ingredients, steps, and safe deletion | Profiles and recipe details | Public recipe list, filters, sorting, and paging |
| 3 | OAuth, security, health, logging foundation, and integration | MinIO, welcome email, deployment, and backup | SEO, accessibility, sitemap, and user docs | Images, resize job, search, Redis, and performance |

Han also owns safe category deletion. Hieu owns recipe archive and external image cleanup. Han owns the recipe database delete flow and its ownership checks.

S = 1, M = 2, and L = 3 are simple planning guides. Minh Anh has lower-risk work at about 70-80% of a normal member's load. Dan has less feature coding because he reviews Pull Requests, solves integration problems, and supports the team. Han and Hieu have more connected feature work, but it follows clear data and media dependencies.

## Git Workflow

1. Pull the latest `main` and choose the assigned Issue.
2. Create one branch, such as `feat/2-category-management`.
3. Build and test the full feature.
4. Push the branch and open a small Pull Request.
5. Dan reviews member Pull Requests. Han reviews Dan's Pull Requests.
6. Merge after review when useful, then delete the branch.

When Cycle 1 is almost complete, create four Cycle 2 Issues. Keep future work in [ROADMAP.md](ROADMAP.md) until then.

## Six Team Rules

1. Work from the latest `main` and use one branch per task.
2. Do not push feature code directly to `main`.
3. Keep a Pull Request small enough for another student to review.
4. Tell the team before changing a shared API, database schema, or common component.
5. A task is done when real data works, important tests pass, and the Pull Request is merged.
6. Ask for help early when blocked or when the deadline may be missed.

## Definition Of Done

- The feature works from UI to API and database when those layers apply.
- Permissions and validation follow the SRS.
- Useful logs and important success and error tests are included.
- Relevant local checks pass and no secrets are committed.
- The Pull Request is merged.
