# Student infomation
| MSSV | Họ Và Tên | Email cá nhân | Tên Tài khoản Github |
|---|---|---|---|
| 2312607 | Nguyễn Ngọc Hân | eric.wk08@gmail.com | meranh05 |
| 2312590 | Nguyễn Ngọc Trường Dân | 2312590@dlu.edu.vn | 0Yaam |
| 2312571 | Nguyễn Minh Anh | nguyenminanh5@gmail.com | MinhAnhhhhhh |
| 2312617 | Trần Xuân Hiếu | 2312617@dlu.edu.vn | ThanhXuanHieu |

# Culinary Blog

Culinary Blog is a student project for sharing cooking recipes. The Agent Bootstrap includes one working path from PostgreSQL to a FastAPI category endpoint and a Next.js category page.

## Technology

- Python, FastAPI, Pydantic, SQLAlchemy 2, and Alembic
- PostgreSQL, Redis, and MinIO
- Next.js App Router, React, and TypeScript
- pytest, Docker Compose, and GitHub Actions

## Requirements

- Git
- Docker Desktop with Docker Compose
- About 4 GB of free memory

Python, uv, Node.js, and npm are needed only when running checks outside Docker.

## Clone And Run

```bash
git clone https://github.com/0Yaam/culinary-blog.git
cd culinary-blog
docker compose up --build
```

The API container runs the database migration and safe seed command at startup. To stop the project:

```bash
docker compose down
```

Do not add `-v` unless you want to delete local database data.

## Main URLs

- Web app: http://localhost:3000
- API documentation: http://localhost:8000/docs
- Health check: http://localhost:8000/health

## Folder Structure

```text
backend/      FastAPI app, migration, seed, and tests
frontend/     Next.js app and category page
docs/         Team guide, roadmap, SRS map, and source PDFs
.github/      CI, Issue template, and Pull Request template
compose.yaml  Local services
```

## Tests

```bash
uv sync --directory backend
uv run --directory backend ruff check .
uv run --directory backend pytest --cov=culinary_blog_api

npm ci --prefix frontend
npm run lint --prefix frontend
npm run build --prefix frontend
```

See [docs/TEAM.md](docs/TEAM.md) for the work split and Git workflow.
