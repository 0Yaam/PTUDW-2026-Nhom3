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
image writes and after resize completion. Issue #61 also records a recipe-cache
generation in the *same database transaction* as every recipe, ingredient,
step, or image change. Each cache lookup reads that committed generation before
using Redis. This prevents another API process from serving an old Redis entry
after a write occurred during a Redis outage; a rolled-back write does not
advance the generation. The Redis version bump remains best-effort, while old
versioned entries expire by TTL.
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

## Issue #61 verification (2026-10-14)

The verification starts from `origin/main` at `ce7cb63` (which includes #57)
and uses only recipe code, migration, tests, and performance tooling. The
transactional cache generation migration is `20261014_0010`. The image worker
now fences each attempt by claim number and holds the job row lock while
writing deterministic variant keys. An expired worker cannot reset a newer
claim or publish stale URLs. The original image remains usable until both
variants finish. PostgreSQL verification also exposed a pre-existing upload
ordering bug: without an explicit flush, SQLAlchemy inserted the resize job
before its parent image, producing a foreign-key 409. The image is now flushed
before the job in the same transaction; a regression test asserts this order.
No REST endpoint or frontend style changes are involved.

These commands run from the repository root in PowerShell. They use a separate
Compose project, volumes, and loopback ports (API 18061, PostgreSQL 15461,
Redis 16361, MinIO 19061), leaving the normal 8000/3000 stack alone:

```powershell
$compose = @('-p', 'culinary-issue61', '-f', 'compose.yaml', '-f', 'backend/perf/compose.issue61.yaml')
docker compose @compose up --build -d postgres redis minio minio-init api image-worker
docker compose @compose exec -T postgres psql -U culinary -d culinary_blog -At -c 'SELECT count(*) FROM recipes WHERE status=1 AND is_deleted=false;'
Get-Content backend/perf/explain_recipe_reads.sql | docker compose @compose exec -T postgres psql -U culinary -d culinary_blog -X -q
```

For the live two-process/outage/resize check, start a peer API process without
rerunning migration/seed, then run the verifier. It creates one temporary
recipe, checks real MinIO WebP dimensions, primes list/search/detail cache on
the peer, stops only the isolated Redis, archives through the first API, and
verifies that the peer never returns stale content after Redis restarts. The
script restarts Redis and deletes the temporary recipe even if an assertion
fails. Start the isolated `file-worker` afterwards if queued objects should
be physically removed.

```powershell
docker compose @compose run -d --no-deps --name culinary-issue61-api-peer -p 127.0.0.1:18062:8000 api uvicorn culinary_blog_api.main:app --host 0.0.0.0 --port 8000
uv run --directory backend python perf/verify_issue61_runtime.py
docker compose @compose up -d file-worker
docker rm -f culinary-issue61-api-peer
```

Run k6 only after the API is healthy. Use `docker run` directly on the isolated
network so the load command cannot recreate Compose dependencies. The script
warms the three paths, waits for the API's per-IP rate-limit window, then runs
100 concurrent virtual users for two minutes:

```powershell
$perfDir = (Resolve-Path backend/perf).Path
docker run --rm --network culinary-issue61_default -e API_URL=http://api:8000 -e RECIPE_SLUG=pho-bo-ha-noi -v "${perfDir}:/scripts:ro" grafana/k6:latest run /scripts/recipe-reads.js
```

To repeat backend checks: `uv sync --directory backend`,
`uv run --directory backend ruff check .`, and
`uv run --directory backend pytest --cov=culinary_blog_api`.

The PostgreSQL seed contained 100 Published recipes. `EXPLAIN (ANALYZE,
BUFFERS)` execution times were 0.186 ms (list, 14 shared buffers hit),
0.102 ms (category-filtered list, 9), 0.099 ms (search, 11), and 0.108 ms
(detail, 7). The first three used small sequential scans with in-memory sorts;
detail used the slug, category, and user indexes. At 100 rows those scans cost
less than 0.2 ms, so this run does not justify another index. Query-count tests
with eight recipes and five ingredients/steps/images per recipe bound uncached
list and search to three SELECTs each and detail to six, including the new
generation SELECT; the count does not grow with collection length.

The live verifier passed with two API processes and two image workers: a
temporary published recipe returned cache `HIT` for list/search/detail, upload
produced both WebP variants at the exact target dimensions, and archive during
an isolated Redis outage was not served stale by the peer after recovery. The
temporary recipe was hard-deleted; its three object-cleanup jobs reached
`Done`. Unit tests additionally cover 1/5/30-minute retry delays, final
fourth-attempt failure, a reclaimed lease, and a stale worker's failure/finish
being fenced off.

The first 100-VU k6 run on the transactional-generation implementation had
200/200 successful measured reads and 97.5% cache hits, but failed latency
thresholds (p50 185.38 ms, p95 1.04 s, p99 about 1.05 s). Logs showed many
generation SELECTs over 100 ms during synchronized bursts. A short-lived
session with a 12-query limit improved p50 to 103.17 ms but left p95 at
586.51 ms. Raising that limit to 20 improved p50 to 55.56 ms but worsened p95
to 698.92 ms; connection fan-out was not the right final fix. Concurrent cache
readers now join a ten-millisecond batch *before* its DB query starts. Each
batch checks the committed generation once, releases its DB connection before
Redis access, and shares that post-arrival snapshot with its waiters. Requests
arriving after the query starts form a new batch, so a later write cannot be
hidden by an older in-flight check. At most 20 batches read concurrently, the
default persistent pool size.

A subsequent 100-VU run after batching still failed p95 at 953.63 ms
(p50 40.65 ms, p99 975.49 ms, 200/200 successful reads, 87% cache hits).
The test warm-up waits 61 seconds for the per-IP rate-limit window, so the
one-minute search entry has expired when the first load burst arrives. Logs
showed 36 slow SELECTs, including many concurrent searches for the same key.
Cold anonymous list/detail/search keys now serialize their DB fill per API
process and key; followers recheck Redis without a second generation SELECT.
This does not change the cache TTL or HTTP contract. A 30-request regression
test asserts that an expired search key triggers exactly one DB load.

With per-key cold-load serialization but a 2 ms generation batch, the same
100-VU script improved to 200/200 successful reads, 99% cache hits, p50
41.56 ms, p95 550.48 ms, and p99 556.14 ms; the p95 threshold still failed.
Increasing only the generation batch window to 10 ms yielded 200/200
successful measured reads, 99% cache hits, p50 44.68 ms, p95 282.71 ms,
and p99 299.28 ms. All three latency thresholds passed. The test runs
100 VUs for two minutes, with two request bursts because each VU sleeps
65 seconds between iterations to respect the app's 100/minute per-IP limit.
`uv sync --directory backend --offline`, backend Ruff, and full pytest with
coverage passed: 146 tests, 89% total coverage. The frontend is unchanged;
`npm ci`, frontend ESLint, a Windows Webpack production build, and a fresh
`docker build --no-cache -t culinary-issue61-frontend frontend` all passed.
The default `npm run build --prefix frontend` on this Windows host hit a
Turbopack internal child-process error while processing the unchanged admin
CSS module; the same default Turbopack build passed inside the production
Linux Dockerfile. No admin/frontend source was altered for this issue.

Local Docker had 16 logical CPUs and approximately 3.8 GiB RAM assigned,
shared with other running containers. This check is evidence for the seeded
local dataset, not certification of the SRS production thresholds on a
dedicated 2-vCPU/4-GiB host or at higher throughput.
