"""Redis cache-aside for anonymous public recipe responses."""

import hashlib
from functools import lru_cache

import structlog
from pydantic import BaseModel
from redis.asyncio import Redis
from redis.exceptions import RedisError

from ..config import get_settings

logger = structlog.get_logger()
VERSION_KEY = "recipes:cache:version"
TTLS = {"list": 15 * 60, "detail": 5 * 60, "search": 60}
_pending_invalidations = 0


@lru_cache
def get_cache_client() -> Redis | None:
    url = get_settings().redis_url
    if not url:
        return None
    try:
        return Redis.from_url(url, socket_connect_timeout=0.2, socket_timeout=0.2)
    except (RedisError, ValueError) as error:
        logger.warning("recipe_cache_configuration_invalid", error_type=type(error).__name__)
        return None


def _key(version: str, kind: str, request_key: str) -> str:
    digest = hashlib.sha256(request_key.encode("utf-8")).hexdigest()
    return f"recipes:cache:{version}:{kind}:{digest}"


async def _flush_pending(client: Redis) -> None:
    global _pending_invalidations
    count = _pending_invalidations
    for _ in range(count):
        await client.incr(VERSION_KEY)
    _pending_invalidations = max(0, _pending_invalidations - count)


async def get_cached[T: BaseModel](
    kind: str, request_key: str, model: type[T]
) -> tuple[str | None, T | None]:
    client = get_cache_client()
    if client is None:
        return None, None
    try:
        await _flush_pending(client)
        version_bytes = await client.get(VERSION_KEY)
        version = version_bytes.decode() if version_bytes else "0"
        payload = await client.get(_key(version, kind, request_key))
        if payload is None:
            return version, None
        return version, model.model_validate_json(payload)
    except (RedisError, ValueError) as error:
        logger.warning("recipe_cache_read_failed", kind=kind, error_type=type(error).__name__)
        return None, None


async def set_cached(kind: str, request_key: str, response: BaseModel, version: str | None) -> None:
    client = get_cache_client()
    if client is None or version is None:
        return
    try:
        current = await client.get(VERSION_KEY)
        if (current.decode() if current else "0") != version:
            return
        await client.set(
            _key(version, kind, request_key), response.model_dump_json(), ex=TTLS[kind]
        )
    except RedisError as error:
        logger.warning("recipe_cache_write_failed", kind=kind, error_type=type(error).__name__)


async def invalidate_recipe_caches() -> None:
    """Advance the shared namespace; old entries expire at their normal TTL."""
    client = get_cache_client()
    if client is None:
        return
    global _pending_invalidations
    _pending_invalidations += 1
    try:
        await _flush_pending(client)
    except RedisError as error:
        logger.warning("recipe_cache_invalidation_failed", error_type=type(error).__name__)
