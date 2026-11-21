"""Per-client request limits shared by every API replica through Redis.

Redis keeps one counter per client, scope and 60-second window, so all replicas
count against the same limit. When Redis is not configured or does not answer,
each process falls back to its own sliding-window log so requests stay limited.
"""

from __future__ import annotations

import asyncio
import math
import time
from collections import deque

import structlog
from redis.exceptions import RedisError

from .recipes.cache import get_cache_client

WINDOW_SECONDS = 60
KEY_PREFIX = "ratelimit"
logger = structlog.get_logger()


async def _redis_hit(scope: str, client: str, maximum: int) -> int | None:
    redis = get_cache_client()
    if redis is None:
        raise LookupError("Redis is not configured")
    now = time.time()
    window = int(now // WINDOW_SECONDS)
    key = f"{KEY_PREFIX}:{scope}:{client}:{window}"
    # One MULTI/EXEC round trip. The window index is part of the key, so refreshing
    # the TTL never extends a window.
    async with redis.pipeline(transaction=True) as pipe:
        pipe.incr(key)
        pipe.expire(key, WINDOW_SECONDS + 1)
        count, _ = await pipe.execute()
    count = int(count)
    if count > maximum:
        return max(1, math.ceil((window + 1) * WINDOW_SECONDS - now))
    return None


async def _local_hit(
    buckets: dict[tuple[str, str], deque[float]],
    lock: asyncio.Lock,
    scope: str,
    client: str,
    maximum: int,
) -> int | None:
    now = time.monotonic()
    async with lock:
        bucket = buckets.setdefault((client, scope), deque())
        while bucket and bucket[0] <= now - WINDOW_SECONDS:
            bucket.popleft()
        if len(bucket) >= maximum:
            return max(1, math.ceil(WINDOW_SECONDS - (now - bucket[0])))
        bucket.append(now)
    return None


async def check_rate_limit(
    buckets: dict[tuple[str, str], deque[float]],
    lock: asyncio.Lock,
    scope: str,
    client: str,
    maximum: int,
) -> int | None:
    """Count one request; return Retry-After seconds when the limit is exceeded."""
    try:
        return await _redis_hit(scope, client, maximum)
    except LookupError:
        pass
    except (RedisError, OSError) as error:
        logger.warning("rate_limit_redis_unavailable", error_type=type(error).__name__)
    return await _local_hit(buckets, lock, scope, client, maximum)
