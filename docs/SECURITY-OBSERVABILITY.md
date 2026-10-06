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

## Secrets

Configure secrets through environment variables and never commit them. The API refuses to start outside development or test when `JWT_SECRET` still uses the default value.
