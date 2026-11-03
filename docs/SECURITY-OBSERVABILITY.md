# Security and observability

## Health checks

- `GET /health` and `GET /health/live` report that the API process is running.
- `GET /health/ready` checks PostgreSQL and configured Redis and MinIO services.
- Readiness returns `503` when a configured dependency is unavailable.

## Request protection

- Google login: 5 requests per minute per client IP.
- Other authentication endpoints: 10 requests per minute per client IP.
- Other `/api/v1` endpoints: 100 requests per minute per client IP.
- Limit errors return RFC 7807 problem details with `429` and `Retry-After`.
- The current limiter is per API process. Move it to Redis in Issue #47 when the API runs multiple replicas.

Responses include clickjacking, MIME sniffing, referrer, and browser permission headers. Authentication responses also use `Cache-Control: no-store`. Production responses include HSTS.

## Request logs

Each request receives a validated `X-Correlation-ID`. Structured logs include the correlation ID, HTTP method, path, status, elapsed milliseconds, and authenticated user ID when available. Requests slower than 500 ms use the `slow_http_request` warning event.

Every write request below `/api/v1` emits `audit_http_request`, including anonymous authentication attempts. Audit entries contain `actor_id`, `actor_type`, route `action`, route-template `resource`, `result`, status, and elapsed time. Request bodies, query strings, authorization headers, passwords, and tokens are never added to the log context.

Background workers use stable result events and job IDs. Retry/failure events include the attempt count and exception type, while success events contain no recipient, URL, token, secret, or uploaded file content.

Use Docker Compose to inspect the API and worker streams locally:

```bash
docker compose logs -f api
docker compose logs -f email-worker image-worker file-worker
```

Filter JSON logs by `correlation_id` for one HTTP request, or by `job_id` for one background job. Client-facing RFC 7807 errors remain generic and never include a server stack trace.

## Secrets

Configure secrets through environment variables and never commit them. The API refuses to start outside development or test when `JWT_SECRET` still uses the default value.

## Cycle 4 hardening

- Recipe image uploads are limited to 5 requests/minute/IP.
- Non-documentation responses use a restrictive Content Security Policy.
- Authenticated write requests emit `audit_http_request` with correlation ID, user ID, method, path, and status.
- `test_release_integration.py` covers register, login, recipe creation, publish, and search as one release flow.
