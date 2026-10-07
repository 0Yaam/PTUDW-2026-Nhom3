import asyncio
import math
import re
import time
import uuid
from collections import deque

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api.health import router as health_router
from .auth import AuthProblem
from .auth import router as auth_router
from .auth.security import read_access_token
from .categories import router as categories_router
from .config import get_settings
from .recipes import RecipeProblem
from .recipes import router as recipes_router

settings = get_settings()
logger = structlog.get_logger()
correlation_id_pattern = re.compile(r"^[A-Za-z0-9._-]{1,128}$")

app = FastAPI(title=settings.app_name, version="0.1.0", docs_url="/docs")
app.state.rate_limit_buckets = {}
app.state.rate_limit_lock = asyncio.Lock()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "If-Match", "X-Correlation-ID"],
)


@app.exception_handler(AuthProblem)
async def auth_problem_handler(_request: Request, error: AuthProblem) -> JSONResponse:
    return JSONResponse(
        status_code=error.status,
        content=error.as_dict(),
        media_type="application/problem+json",
    )


@app.exception_handler(RecipeProblem)
async def recipe_problem_handler(_request: Request, error: RecipeProblem) -> JSONResponse:
    return JSONResponse(
        status_code=error.status,
        content=error.as_dict(),
        media_type="application/problem+json",
    )


@app.exception_handler(RequestValidationError)
async def validation_problem_handler(
    _request: Request, error: RequestValidationError
) -> JSONResponse:
    errors: dict[str, list[str]] = {}
    for item in error.errors():
        field = ".".join(str(part) for part in item["loc"] if part != "body") or "body"
        errors.setdefault(field, []).append(item["msg"])
    return JSONResponse(
        status_code=422,
        media_type="application/problem+json",
        content={
            "type": "VALIDATION_ERROR",
            "title": "Validation Error",
            "status": 422,
            "detail": "One or more fields are invalid.",
            "errors": errors,
        },
    )


def _rate_limit(path: str) -> tuple[str, int] | None:
    if path == "/api/v1/auth/google":
        return "google-auth", 5
    if path.startswith("/api/v1/auth/"):
        return "auth", 10
    if path.startswith("/api/v1/recipes/") and path.endswith("/images"):
        return "upload", 5
    if path.startswith("/api/v1/"):
        return "api", 100
    return None


def _add_security_headers(response, path: str) -> None:
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if path not in {"/docs", "/openapi.json", "/redoc"}:
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
        )
    if settings.environment.lower() == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    if path.startswith("/api/v1/auth/"):
        response.headers["Cache-Control"] = "no-store"


async def _rate_limit_response(request: Request) -> JSONResponse | None:
    limit = _rate_limit(request.url.path)
    if limit is None:
        return None

    scope, maximum = limit
    now = time.monotonic()
    client_ip = request.client.host if request.client else "unknown"
    key = (client_ip, scope)
    # ponytail: per-process limiter; move to Redis when Issue #47 adds shared cache.
    async with app.state.rate_limit_lock:
        bucket = app.state.rate_limit_buckets.setdefault(key, deque())
        while bucket and bucket[0] <= now - 60:
            bucket.popleft()
        if len(bucket) >= maximum:
            retry_after = max(1, math.ceil(60 - (now - bucket[0])))
            return JSONResponse(
                status_code=429,
                media_type="application/problem+json",
                headers={"Retry-After": str(retry_after)},
                content={
                    "type": "RATE_LIMIT_EXCEEDED",
                    "title": "Too Many Requests",
                    "status": 429,
                    "detail": "Too many requests. Try again later.",
                },
            )
        bucket.append(now)
    return None


@app.middleware("http")
async def request_context(request: Request, call_next):
    incoming_id = request.headers.get("X-Correlation-ID", "")
    correlation_id = (
        incoming_id if correlation_id_pattern.fullmatch(incoming_id) else str(uuid.uuid4())
    )
    started = time.perf_counter()
    user_id = None
    authorization = request.headers.get("Authorization", "")
    if authorization.startswith("Bearer "):
        token_user_id = read_access_token(authorization.removeprefix("Bearer "))
        user_id = str(token_user_id) if token_user_id else None

    try:
        response = await _rate_limit_response(request) or await call_next(request)
    except Exception:
        logger.exception("unhandled_request_error", correlation_id=correlation_id)
        response = JSONResponse(
            status_code=500,
            media_type="application/problem+json",
            content={
                "type": "INTERNAL_SERVER_ERROR",
                "title": "Internal Server Error",
                "status": 500,
                "detail": "The request could not be completed.",
            },
        )

    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    response.headers["X-Correlation-ID"] = correlation_id
    _add_security_headers(response, request.url.path)
    log = logger.warning if elapsed_ms > 500 else logger.info
    log(
        "slow_http_request" if elapsed_ms > 500 else "http_request",
        correlation_id=correlation_id,
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        elapsed_ms=elapsed_ms,
        user_id=user_id,
    )
    return response


app.include_router(health_router)
app.include_router(auth_router)
app.include_router(categories_router)
app.include_router(recipes_router)
