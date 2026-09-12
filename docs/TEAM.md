# Team Guide

Group 3, CTK47A uses one repository, feature branches, Pull Requests, and the [GitHub Project](https://github.com/users/0Yaam/projects/1).

## Members

| Name | Student ID | GitHub | Role |
|---|---:|---|---|
| Nguyen Ngoc Truong Dan | 2312590 | `0Yaam` | Team leader |
| Nguyen Ngoc Han | 2312607 | `Meranh05` | Member |
| Nguyen Minh Anh | 2312571 | `MinhAnhhhhhh` | Member |
| Tran Xuan Hieu | 2312617 | `ThanhXuanHieu` | Member |

Each owner completes the database, API, UI, and tests for a feature when those layers apply. Shared rules and components have one owner. Other members reuse them.

## Find Your Task

1. Open the GitHub Project.
2. Use **Current Work** to see Ready, In Progress, and Review items.
3. Open the Ready Issue assigned to you.
4. Work on only one In Progress Issue at a time.
5. Ask Dan for the next Ready task after your current task is Done. Do not choose a random Backlog item.

Project Status is the source of current task status. Roadmap files do not copy changing status.

## Git And Pull Request Flow

1. Open your assigned Ready Issue and move it to In Progress.
2. Update local `main` and create `feat/<issue-number>-<short-name>`.
3. Implement and test the feature.
4. Push the branch and open a Pull Request.
5. Link the Issue. Use `Closes #N` only when the Pull Request completes it.
6. Move the Issue to Review when the complete feature is ready.
7. Fix CI and review feedback.
8. Merge after one approval and all required checks pass.
9. Delete the branch, then ask for the next Ready task.

Dan reviews member Pull Requests. Han reviews Dan's Pull Requests. A large feature may use several small linked Pull Requests.

PR titles use this format:

```text
Full Name - Student ID: short English title
```

Example: `Nguyễn Ngọc Hân - 2312607: add category management`

## Six Team Rules

1. Start from current `main`; do not push feature work directly to `main`.
2. Work on one In Progress Issue at a time.
3. Keep Pull Requests small enough to review.
4. Tell the team before changing a shared API, model, error shape, or component.
5. Never commit secrets or production test identities.
6. Ask early when blocked or late.

## Definition Of Done

- Acceptance criteria and SRS rules are met.
- Database, API, UI, and tests work together when they apply.
- Validation, permissions, and useful errors are included.
- Relevant local checks and required CI checks pass.
- Documentation changes are included when needed.
- The Pull Request has the required review and is merged.

## Shared Foundation

All Cycle 1 work uses these rules:

- Run locally with `docker compose up --build`.
- Put HTTP routes under `/api/v1`.
- Use explicit request and response schemas.
- Return the existing RFC 7807-style error shape: `type`, `title`, `status`, and `detail`.
- Create schema changes with Alembic; do not edit a shared migration after merge.
- Keep the existing frontend layout and loading, empty, and error patterns.
- Use development seed data only in development and tests.

The current seed has categories but no Admin or Author identity. Cycle 1 tasks may start with documented test fixtures or local mock identity adapters on their own branches. Those helpers must be disabled outside development and tests. Merge the real user/auth model from Issue #1 before category or recipe permission integration is complete.
