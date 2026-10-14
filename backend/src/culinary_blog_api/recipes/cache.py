"""Redis cache-aside for anonymous public recipe responses."""

import asyncio
import hashlib
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from functools import lru_cache
from weakref import WeakKeyDictionary, WeakValueDictionary

import structlog
from pydantic import BaseModel
from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy import event, insert, select, update
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import SessionFactory
from .model import (
    Recipe,
    RecipeCacheGeneration,
    RecipeImage,
    RecipeIngredient,
    RecipeStep,
)

logger = structlog.get_logger()
VERSION_KEY = "recipes:cache:version"
TTLS = {"list": 15 * 60, "detail": 5 * 60, "search": 60}
_pending_invalidations = 0
_CACHED_MODELS = (Recipe, RecipeImage, RecipeIngredient, RecipeStep)
_GENERATION_READ_LIMIT = 20
_GENERATION_BATCH_SECONDS = 0.010
_generation_limiters: WeakKeyDictionary[asyncio.AbstractEventLoop, asyncio.Semaphore] = (
    WeakKeyDictionary()
)


@dataclass
class _GenerationBatch:
    waiters: list[asyncio.Future[str]] = field(default_factory=list)


_generation_batches: WeakKeyDictionary[asyncio.AbstractEventLoop, _GenerationBatch] = (
    WeakKeyDictionary()
)
_fill_locks: WeakKeyDictionary[
    asyncio.AbstractEventLoop, WeakValueDictionary[str, asyncio.Lock]
] = WeakKeyDictionary()


def _generation_limiter() -> asyncio.Semaphore:
    loop = asyncio.get_running_loop()
    limiter = _generation_limiters.get(loop)
    if limiter is None:
        limiter = asyncio.Semaphore(_GENERATION_READ_LIMIT)
        _generation_limiters[loop] = limiter
    return limiter


@event.listens_for(Session, "after_flush")
def _advance_committed_generation(session: Session, _flush_context: object) -> None:
    """Advance with the recipe write, never after a separate Redis operation."""
    changed = any(isinstance(row, _CACHED_MODELS) for row in session.new | session.deleted)
    changed |= any(
        isinstance(row, _CACHED_MODELS) and session.is_modified(row, include_collections=False)
        for row in session.dirty
    )
    if not changed:
        return
    connection = session.connection()
    result = connection.execute(
        update(RecipeCacheGeneration)
        .where(RecipeCacheGeneration.id == 1)
        .values(version=RecipeCacheGeneration.version + 1)
    )
    if result.rowcount == 0:
        # SQLite create_all tests have no migration seed row. PostgreSQL does.
        connection.execute(insert(RecipeCacheGeneration).values(id=1, version=1))


async def _read_generation_batch(batch: _GenerationBatch) -> None:
    try:
        async with _generation_limiter():
            async with SessionFactory() as session:
                version = await session.scalar(
                    select(RecipeCacheGeneration.version).where(RecipeCacheGeneration.id == 1)
                )
    except Exception as error:
        for waiter in batch.waiters:
            if not waiter.done():
                waiter.set_exception(error)
    else:
        for waiter in batch.waiters:
            if not waiter.done():
                waiter.set_result(str(version or 0))


def _start_generation_batch(
    loop: asyncio.AbstractEventLoop, batch: _GenerationBatch
) -> None:
    # A request arriving after dispatch cannot join an in-flight DB read.
    if _generation_batches.get(loop) is batch:
        del _generation_batches[loop]
    loop.create_task(_read_generation_batch(batch))


async def _committed_generation() -> str:
    """Share one post-arrival DB check among a brief burst of cache reads."""
    loop = asyncio.get_running_loop()
    batch = _generation_batches.get(loop)
    if batch is None:
        batch = _GenerationBatch()
        _generation_batches[loop] = batch
        loop.call_later(_GENERATION_BATCH_SECONDS, _start_generation_batch, loop, batch)
    waiter: asyncio.Future[str] = loop.create_future()
    batch.waiters.append(waiter)
    return await waiter


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
    generation = await _committed_generation()
    try:
        await _flush_pending(client)
        version_bytes = await client.get(VERSION_KEY)
        version = f"{generation}:{version_bytes.decode() if version_bytes else '0'}"
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
        if (current.decode() if current else "0") != version.rsplit(":", 1)[1]:
            return
        await client.set(
            _key(version, kind, request_key), response.model_dump_json(), ex=TTLS[kind]
        )
    except RedisError as error:
        logger.warning("recipe_cache_write_failed", kind=kind, error_type=type(error).__name__)


async def get_or_load_cached[T: BaseModel](
    kind: str,
    request_key: str,
    model: type[T],
    load: Callable[[], Awaitable[T]],
    *,
    cache_if: Callable[[T], bool] | None = None,
) -> tuple[str, T]:
    """Serialize a cold key's DB load inside one process; never cache private data."""
    version, cached = await get_cached(kind, request_key, model)
    if cached is not None:
        return "HIT", cached
    if version is None:
        return "BYPASS", await load()

    loop = asyncio.get_running_loop()
    locks = _fill_locks.get(loop)
    if locks is None:
        locks = WeakValueDictionary()
        _fill_locks[loop] = locks
    lock_key = _key(version, kind, request_key)
    lock = locks.get(lock_key)
    if lock is None:
        lock = asyncio.Lock()
        locks[lock_key] = lock
    async with lock:
        # The initial DB generation was checked after this request arrived.
        # Recheck only Redis here, avoiding another SELECT for every cold read.
        client = get_cache_client()
        if client is None:
            return "BYPASS", await load()
        try:
            await _flush_pending(client)
            current = await client.get(VERSION_KEY)
            current_matches = (
                (current.decode() if current else "0") == version.rsplit(":", 1)[1]
            )
            payload = await client.get(lock_key) if current_matches else None
            cached = model.model_validate_json(payload) if payload is not None else None
        except (RedisError, ValueError) as error:
            logger.warning("recipe_cache_read_failed", kind=kind, error_type=type(error).__name__)
            return "BYPASS", await load()
        if not current_matches:
            return "BYPASS", await load()
        if cached is not None:
            return "HIT", cached
        result = await load()
        if cache_if is None or cache_if(result):
            await set_cached(kind, request_key, result, version)
        return "MISS", result


async def invalidate_recipe_caches() -> None:
    """Best-effort Redis bump; the transactional DB generation is authoritative."""
    client = get_cache_client()
    if client is None:
        return
    global _pending_invalidations
    _pending_invalidations += 1
    try:
        await _flush_pending(client)
    except RedisError as error:
        logger.warning("recipe_cache_invalidation_failed", error_type=type(error).__name__)
