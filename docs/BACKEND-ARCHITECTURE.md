# Backend architecture

The backend keeps Clean Architecture responsibilities inside small feature folders instead
of duplicating the same four top-level folders for every feature.

| Responsibility | Location |
| --- | --- |
| Domain entities and rules | `backend/src/culinary_blog_api/*/model.py` |
| Application use cases | `backend/src/culinary_blog_api/*/service.py` |
| HTTP presentation | `backend/src/culinary_blog_api/*/router.py` and `schemas.py` |
| Infrastructure | `db.py`, `config.py`, `migrations/`, and `seed.py` |

Routes contain HTTP concerns only. Services coordinate validation and database work. Models
define persisted entities and constraints. Infrastructure owns configuration, sessions,
migrations, and development data. New HTTP routes remain under `/api/v1`.

## Lab 2 data model

- `Category` groups recipes.
- `Recipe` belongs to one category and one author.
- `Ingredient` stores reusable ingredient names.
- `RecipeIngredient` stores a recipe's quantity, unit, and display order.
- `RecipeStep` stores ordered preparation instructions.

Migration `20260922_0004` adds the ingredient and preparation-step tables. The seed command is
idempotent and creates at least 20 categories and 100 recipes. Every generated recipe has at
least 10 ingredients and 5 preparation steps.

## Verify

```bash
docker compose up -d postgres
docker compose run --rm api alembic upgrade head
docker compose run --rm api seed
docker compose exec -T postgres psql -U culinary -d culinary_blog -c \
  "SELECT COUNT(*) AS categories FROM categories; SELECT COUNT(*) AS recipes FROM recipes;"
uv run --directory backend pytest tests/test_seed.py
```
