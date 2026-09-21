# Coding Agent Guide

## Before Coding

1. Read the GitHub Issue and its Done when list.
2. Read the related items in `docs/SRS-MAP.md` and the source SRS.
3. Inspect the current code and tests before choosing a design.
4. Keep the change inside the Issue. Do not mark future roadmap work as complete.

## While Coding

- Make the smallest complete change that connects the needed layers.
- Keep HTTP routes under `/api/v1`.
- Return RFC 7807 errors without stack traces.
- Check permissions in the backend. Authors may change only their own resources.
- Validate input and avoid N+1 database queries.
- Check upload MIME type, magic bytes, and the 5 MB limit.
- Do not commit secrets. Add new settings to the correct `.env.example`.
- Update documentation when an API, database schema, or shared component changes.

## Checks

Run the checks that match the change. Before a Pull Request, run all checks when practical:

```bash
uv sync --directory backend
uv run --directory backend ruff check .
uv run --directory backend pytest --cov=culinary_blog_api
npm ci --prefix frontend
npm run lint --prefix frontend
npm run build --prefix frontend
```

Use `.\start-all.ps1` to build and start PostgreSQL, the backend, and the
production-style frontend container. Run `npm run dev --prefix frontend` in
another terminal only when frontend hot reload is useful; it runs on port 3001
while the Docker frontend remains on port 3000. Run migrations with
`docker compose exec api alembic upgrade head` and seed data with
`docker compose exec api seed`.

Never claim that a check passed unless you ran it and saw a successful result.
