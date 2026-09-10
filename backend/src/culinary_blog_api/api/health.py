from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session

router = APIRouter(tags=["health"])


@router.get("/health/live")
async def live() -> dict[str, str]:
    return {"status": "Healthy"}


@router.get("/health/ready")
async def ready(
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, object]:
    try:
        await session.execute(text("SELECT 1"))
    except Exception:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "Unhealthy", "entries": {"database": "Unhealthy"}}
    return {"status": "Healthy", "entries": {"database": "Healthy"}}


@router.get("/health")
async def health(
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, object]:
    return await ready(response, session)
