import asyncio
import ssl
from typing import Annotated
from urllib.parse import unquote, urlsplit

import httpx
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..db import get_session

router = APIRouter(tags=["health"])


async def _redis_ready(url: str) -> bool:
    parsed = urlsplit(url)
    if parsed.scheme not in {"redis", "rediss"} or not parsed.hostname:
        return False
    writer = None
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(
                parsed.hostname,
                parsed.port or 6379,
                ssl=ssl.create_default_context() if parsed.scheme == "rediss" else None,
            ),
            timeout=2,
        )
        if parsed.password:
            parts = ["AUTH"]
            if parsed.username:
                parts.append(unquote(parsed.username))
            parts.append(unquote(parsed.password))
            command = f"*{len(parts)}\r\n" + "".join(
                f"${len(part.encode())}\r\n{part}\r\n" for part in parts
            )
            writer.write(command.encode())
            await writer.drain()
            if not (await asyncio.wait_for(reader.readline(), timeout=2)).startswith(b"+OK"):
                return False
        writer.write(b"*1\r\n$4\r\nPING\r\n")
        await writer.drain()
        return (await asyncio.wait_for(reader.readline(), timeout=2)).startswith(b"+PONG")
    except (OSError, TimeoutError, ValueError):
        return False
    finally:
        if writer is not None:
            writer.close()
            await writer.wait_closed()


async def _minio_ready(endpoint: str) -> bool:
    try:
        async with httpx.AsyncClient(timeout=2) as client:
            response = await client.get(f"{endpoint.rstrip('/')}/minio/health/ready")
        return response.status_code == status.HTTP_200_OK
    except httpx.HTTPError:
        return False


@router.get("/health/live")
async def live() -> dict[str, str]:
    return {"status": "Healthy"}


@router.get("/health/ready")
async def ready(
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, object]:
    settings = get_settings()
    entries: dict[str, str] = {}
    try:
        await session.execute(text("SELECT 1"))
        entries["database"] = "Healthy"
    except Exception:
        entries["database"] = "Unhealthy"

    entries["redis"] = (
        "Healthy" if await _redis_ready(settings.redis_url) else "Unhealthy"
    ) if settings.redis_url else "Disabled"
    entries["minio"] = (
        "Healthy" if await _minio_ready(settings.minio_endpoint) else "Unhealthy"
    ) if settings.minio_endpoint else "Disabled"

    healthy = "Unhealthy" not in entries.values()
    if not healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": "Healthy" if healthy else "Unhealthy", "entries": entries}


@router.get("/health")
async def health(
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, object]:
    return await ready(response, session)
