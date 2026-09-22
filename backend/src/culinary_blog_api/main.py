import time
import uuid

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api.health import router as health_router
from .auth import AuthProblem
from .auth import router as auth_router
from .categories import router as categories_router
from .config import get_settings
from .recipes import RecipeProblem
from .recipes import router as recipes_router

settings = get_settings()
logger = structlog.get_logger()

app = FastAPI(title=settings.app_name, version="0.1.0", docs_url="/docs")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Correlation-ID"],
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


@app.middleware("http")
async def request_context(request: Request, call_next):
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    started = time.perf_counter()
    try:
        response = await call_next(request)
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
    logger.info(
        "http_request",
        correlation_id=correlation_id,
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        elapsed_ms=elapsed_ms,
    )
    return response


app.include_router(health_router)
app.include_router(auth_router)
app.include_router(categories_router)
app.include_router(recipes_router)
