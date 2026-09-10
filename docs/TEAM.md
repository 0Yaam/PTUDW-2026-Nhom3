# Team Guide

## Team

| Name | Student ID | GitHub | Role |
|---|---:|---|---|
| Nguyen Ngoc Truong Dan | 2312590 | `0Yaam` | Team leader |
| Nguyen Ngoc Han | 2312607 | `Meranh05` | Member |
| Nguyen Minh Anh | 2312571 | `MinhAnhhhhhh` | Member |
| Tran Xuan Hieu | 2312617 | `ThanhXuanHieu` | Member |

## Work Split

Each member owns vertical feature work across the database, API, UI, and tests when those layers apply. Minh Anh has lower-risk work at about 70-80% of a normal load. Dan has a smaller coding load so he has time for review, integration, and team support.

The full plan is in [ROADMAP.md](ROADMAP.md).

## Current Work Cycle

Cycle 1 builds the core data and access features.

| Owner | First task | Reviewer |
|---|---|---|
| Dan | Local registration and login | Han |
| Han | Create and update categories | Dan |
| Minh Anh | Category detail and simple recipe cards | Dan |
| Hieu | Draft recipe creation and the base Recipe model | Dan |

The Category list on the home page is **Agent Bootstrap** work. It is not student work.

## Git Workflow

1. Choose the assigned Issue and pull the latest `main`.
2. Create one feature branch, for example `feat/2-local-login`.
3. Build and test the task.
4. Push the branch and open a small Pull Request.
5. The reviewer checks it. Dan merges after CI passes.
6. Delete the branch and then start the next Issue.

Dan reviews member Pull Requests. Han reviews Dan's Pull Requests. Another free member may review when needed.

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
- Important success and error cases are tested.
- CI passes.
- No secrets are committed.
- The Pull Request is reviewed and merged.
