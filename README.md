# Culinary Blog

Culinary Blog is a student project for sharing cooking recipes. The current bootstrap has one working path from PostgreSQL to a FastAPI category endpoint and a Next.js page.

## Stack

- Python, FastAPI, Pydantic, SQLAlchemy 2, and Alembic
- PostgreSQL, Redis, MinIO, and background jobs when required by the SRS
- Next.js App Router, React, and TypeScript
- pytest, Docker Compose, and GitHub Actions

The source SRS describes a .NET backend. Group 3 keeps the same requirements but uses FastAPI and SQLAlchemy. Requirement codes remain unchanged in [docs/SRS-MAP.md](docs/SRS-MAP.md).

## Run

Requirements: Git, Docker Desktop with Docker Compose, and about 4 GB of free memory.

```bash
git clone https://github.com/0Yaam/PTUDW-2026-Nhom3.git
cd PTUDW-2026-Nhom3
docker compose up --build
```

The API runs migrations and development seed data at startup. Stop it with:

```bash
docker compose down
```

Do not add `-v` unless you want to delete local database data.

## Main URLs

- Web app: http://localhost:3000
- API documentation: http://localhost:8000/docs
- Health check: http://localhost:8000/health

## Checks

Python, uv, Node.js, and npm are needed for checks outside Docker.

```bash
uv sync --locked --directory backend
uv run --directory backend ruff check .
uv run --directory backend pytest --cov=culinary_blog_api --cov-fail-under=80

npm ci --prefix frontend
npm run lint --prefix frontend
npm run typecheck --prefix frontend
npm test --if-present --prefix frontend
npm run build --prefix frontend

docker compose config --quiet
```

## Team Links

- [GitHub Project](https://github.com/users/0Yaam/projects/1) — current task status
- [Team guide](docs/TEAM.md) — workflow and team rules
- [Roadmap](docs/ROADMAP.md) — feature ownership and dependencies
- [SRS map](docs/SRS-MAP.md) — requirement coverage
