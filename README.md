<div align="center">

# Culinary Blog - TEAM 3

**A bilingual recipe publishing platform with a modern food website and role-based Admin workspace.**

![Next.js](https://img.shields.io/badge/Next.js-16-000000?logo=nextdotjs&logoColor=white)
![React](https://img.shields.io/badge/React-19-149ECA?logo=react&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-strict-3178C6?logo=typescript&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.141-009688?logo=fastapi&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)
![i18n](https://img.shields.io/badge/i18n-VI%20%7C%20EN-6D5DFB)

[Quick Start](#quick-start) · [Technology](#technology-stack) · [URLs](#development-urls) · [Checks](#quality-checks) · [Team](#team)

</div>

## Team

| MSSV    | Họ và tên              | Email                   | GitHub                                            |
| ---------| ------------------------| -------------------------| ---------------------------------------------------|
| 2312607 | Nguyễn Ngọc Hân        | eric.wk08@gmail.com     | [Meranh05](https://github.com/Meranh05)           |
| 2312590 | Nguyễn Ngọc Trường Dân | 2312590@dlu.edu.vn      | [0Yaam](https://github.com/0Yaam)                 |
| 2312571 | Nguyễn Minh Anh        | nguyenminanh5@gmail.com | [MinhAnhhhhhh](https://github.com/MinhAnhhhhhh)   |
| 2312617 | Trần Xuân Hiếu         | 2312617@dlu.edu.vn      | [ThanhXuanHieu](https://github.com/ThanhXuanHieu) |

## Work Assignment

| Issue | Main work | Assigned member | SRS | Status |
| --- | --- | --- | --- | --- |
| [#1](https://github.com/0Yaam/PTUDW-2026-Nhom3/issues/1) | Local registration and login: User migration, auth API, UI, validation, security tests | Nguyễn Ngọc Trường Dân (`0Yaam`) | FR-AUTH-001, FR-AUTH-002, NFR-SEC-001 | Completed |
| [#2](https://github.com/0Yaam/PTUDW-2026-Nhom3/issues/2) | Admin category creation and update: API, UI, authorization, tests | Nguyễn Ngọc Hân (`Meranh05`) | FR-CAT-003, FR-CAT-004 | Completed |
| [#3](https://github.com/0Yaam/PTUDW-2026-Nhom3/issues/3) | Category detail page: detail API, recipe list, empty and not-found states | Nguyễn Minh Anh (`MinhAnhhhhhh`) | FR-CAT-002 | Completed |
| [#4](https://github.com/0Yaam/PTUDW-2026-Nhom3/issues/4) | Draft recipe creation: recipe API, form, validation, integration tests | Trần Xuân Hiếu (`ThanhXuanHieu`) | FR-RCP-003 | Completed |

The assigned member owns the implementation and tests for the Issue. Dân coordinates
integration and reviews team Pull Requests. Each change is developed on its own branch
before being merged into `main`.

**Read more:** [Full work assignment and three-cycle plan on GitHub Projects](https://github.com/users/0Yaam/projects/1/views/3)

## Overview

Small Kitchen is a student project for sharing cooking recipes. The current
working flow connects PostgreSQL, a FastAPI REST API, and a Next.js App Router
frontend. Category administration supports Admin authorization, validation,
stable slugs, explicit slug editing, and English/Vietnamese interface text.

## Technology Stack

| Layer    | Technologies                                                              |
| ----------| ---------------------------------------------------------------------------|
| Frontend | Next.js 16, React 19, TypeScript, next-intl, CSS Modules                  |
| Backend  | Python 3.12+, FastAPI, Pydantic, SQLAlchemy 2, Alembic, Uvicorn           |
| Data     | PostgreSQL 16; Redis and MinIO are available as optional Compose services |
| Quality  | pytest, pytest-cov, Ruff, ESLint, Next.js production build                |
| Tooling  | uv, npm, Docker Compose, Git, GitHub                                      |

## Requirements

- Git
- Docker Desktop with Docker Compose
- Node.js 20+ and npm for the frontend development server
- About 4 GB of free memory
- `uv` only when running backend checks directly on the host

## Quick Start

Clone the correct team repository:

```powershell
git clone https://github.com/0Yaam/PTUDW-2026-Nhom3.git
cd PTUDW-2026-Nhom3
```

### Terminal 1 — full system

```powershell
.\start-all.ps1
```

The default command builds and starts PostgreSQL, the FastAPI backend, and the
production-style frontend container. The API container automatically runs
database migrations and the safe seed command.

### Terminal 2 — optional frontend with hot reload

Install dependencies the first time, or whenever `package-lock.json` changes:

```powershell
npm ci --prefix frontend
```

Start an additional Next.js development server on port `3001`:

```powershell
npm run dev --prefix frontend
```

You may use the equivalent helper command:

```powershell
.\start-all.ps1 -Mode frontend
```

Edits inside `frontend/` are reflected at `http://localhost:3001` without
rebuilding the Docker frontend at `http://localhost:3000`.

## Development URLs

| Service             | URL                                                                              |
| ---------------------| ----------------------------------------------------------------------------------|
| Frontend Web        | [http://localhost:3000](http://localhost:3000)                                   |
| Frontend Hot Reload | [http://localhost:3001](http://localhost:3001)                                   |
| Backend API Swagger | [http://localhost:8000/docs](http://localhost:8000/docs)                         |
| Backend Healthcheck | [http://localhost:8000/health](http://localhost:8000/health)                     |


Useful commands:

```powershell
docker compose ps
docker compose logs -f
.\start-all.ps1 -Mode down
```

Stop the frontend development server with `Ctrl+C`. Do not add `-v` to the
Docker shutdown command unless you intentionally want to delete local database
data.

## Frontend Development Modes

The default command always starts the complete Docker system:

```powershell
.\start-all.ps1
```

Run `npm run dev --prefix frontend` only when you also want realtime frontend
updates. The backend accepts local browser requests from both ports `3000` and
`3001`, so both frontend versions can run at the same time.

## Folder Structure

```text
backend/       FastAPI application, migrations, seed, and tests
frontend/      Next.js application and Admin category workspace
docs/          Team guide, roadmap, SRS map, and implementation notes
.github/       Issue and Pull Request templates
compose.yaml   Local Docker services
start-all.ps1  Setup, frontend development, checks, and shutdown helper
```

## Quality Checks

Run the complete project gate:

```powershell
.\start-all.ps1 -Mode check
```

Or run each group directly:

```powershell
uv sync --directory backend
uv run --directory backend ruff check .
uv run --directory backend pytest --cov=culinary_blog_api

npm ci --prefix frontend
npm run lint --prefix frontend
npm run build --prefix frontend
```


See [docs/TEAM.md](docs/TEAM.md) for the work split and Git workflow.
