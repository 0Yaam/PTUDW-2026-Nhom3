# Recipe image resize and performance (Issue #47)

`POST /api/v1/recipes/{id}/images` still returns `201` after the original file and
image row are stored. The same database transaction inserts one
`RecipeImageResizeJob`. The separate `image-worker` reads the original through
`FileStorage`, center-crops 800x600 and 300x300 WebP variants, and fills the
nullable `mediumUrl` and `thumbnailUrl` fields. Until it finishes, clients can
show `originalUrl`. EXIF orientation and transparency are preserved. The worker
claims due jobs in PostgreSQL with `FOR UPDATE SKIP LOCKED`; a five-minute lease
allows recovery after a crash. Failures retry after 1, 5, and 30 minutes, then
the fourth failure marks the job `Failed`. The deterministic variant keys make
retries overwrite the same objects. Image deletion removes both variants even
if metadata has not yet been updated.

The object store contract adds `upload_variant(data, recipe_id, image_id, size)`
and `delete_variant(recipe_id, image_id, size)`, where `size` is `medium` or
`thumbnail`. Public URLs still pass the storage adapter's bucket/key checks.
No new HTTP endpoint is exposed.

Redis caches anonymous public recipe list (15 minutes), published detail (5
minutes), and search (1 minute). Authenticated reads bypass Redis. A shared
version key changes after committed recipe, step, publication, archive, and
image writes and after resize completion. Old versioned entries expire by TTL.
`X-Recipe-Cache` reports `HIT`, `MISS`, or `BYPASS` for read diagnostics. If
Redis is unavailable, reads query PostgreSQL; `/health/ready` reports Redis
unhealthy. Run `docker compose up --build -d` to start Redis and the image
worker with the API. Local backend runs without Redis when `REDIS_URL` is empty.

The PostgreSQL SQLAlchemy pool defaults to 20 persistent connections and 80
overflow connections per API instance. SQL statements exceeding 100 ms emit
`slow_database_query` with duration and operation but no bind values. The
recipe list/search queries select their category in the same statement; detail
uses bounded `selectinload` queries for ingredients, steps, and images.

## Verification

Run `uv run --directory backend pytest --cov=culinary_blog_api` and
`uv run --directory backend ruff check .`. To inspect real PostgreSQL plans on
representative seed data, run:

```powershell
Get-Content backend/perf/explain_recipe_reads.sql | docker compose exec -T postgres psql -U culinary -d culinary_blog
```

Review actual time, buffers, scan/sort choices, and row estimates before
adding any index. The existing search vector has a GIN index. A tiny local
dataset can correctly use a sequential scan; this is not itself a performance
failure.

On 2026-10-06, the local PostgreSQL seed had 100 published recipes. The four
plans above took 0.231 ms (list), 1.138 ms (category-filtered list), 0.749 ms
(full-text search), and 0.767 ms (detail). PostgreSQL used the category B-tree
index for the filtered list and the slug index for detail; it used a sequential
scan for the two small unrestricted sets.
No new index was justified by these plans; repeat the review with larger,
representative data before production.

With a known published slug, run k6 from the host:

```powershell
$env:RECIPE_SLUG = 'pho-bo-ha-noi'
k6 run backend/perf/recipe-reads.js
```

The script warms list/detail/search and runs 100 virtual users for two minutes.
Each user makes one request per 65 seconds so the existing API limit of 100
requests/minute per source IP does not turn a single-machine test into 429s.
This is a concurrency smoke test, not a high-throughput stress test.
It checks cache hit rate >= 80% and read p50 <= 150 ms, p95 <= 500 ms, p99 <=
1000 ms. These local results depend on the host. The SRS production thresholds
also cover write APIs and require production-like hardware/traffic before they
can be claimed as fully met.

The local Docker run on 2026-10-06 used 100 virtual users and recorded 200
successful measured GET requests: cache hit rate 98%, p50 16.95 ms, p95
273.07 ms, and p99 282.81 ms. Its warm-up generated three additional GETs.
