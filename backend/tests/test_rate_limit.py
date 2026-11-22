import asyncio

from redis.exceptions import ConnectionError as RedisConnectionError

from culinary_blog_api import rate_limit


class CounterRedis:
    """Minimal async Redis double shared by two simulated API replicas."""

    def __init__(self) -> None:
        self.values: dict[str, int] = {}
        self.ttls: dict[str, int] = {}

    async def incr(self, key: str) -> int:
        self.values[key] = self.values.get(key, 0) + 1
        return self.values[key]

    async def expire(self, key: str, seconds: int) -> bool:
        self.ttls[key] = seconds
        return True

    def pipeline(self, transaction: bool = True) -> "CounterPipeline":
        assert transaction
        return CounterPipeline(self)


class CounterPipeline:
    def __init__(self, redis: CounterRedis) -> None:
        self.redis = redis
        self.calls: list[tuple[str, tuple]] = []

    async def __aenter__(self) -> "CounterPipeline":
        return self

    async def __aexit__(self, *_exc) -> None:
        return None

    def incr(self, key: str) -> "CounterPipeline":
        self.calls.append(("incr", (key,)))
        return self

    def expire(self, key: str, seconds: int) -> "CounterPipeline":
        self.calls.append(("expire", (key, seconds)))
        return self

    async def execute(self) -> list:
        return [await getattr(self.redis, name)(*args) for name, args in self.calls]


class BrokenRedis:
    def pipeline(self, transaction: bool = True):
        raise RedisConnectionError("down")


async def test_redis_limit_is_shared_between_replicas(monkeypatch) -> None:
    redis = CounterRedis()
    monkeypatch.setattr(rate_limit, "get_cache_client", lambda: redis)
    replica_a = ({}, asyncio.Lock())
    replica_b = ({}, asyncio.Lock())

    results = []
    for index in range(4):
        buckets, lock = replica_a if index % 2 == 0 else replica_b
        results.append(await rate_limit.check_rate_limit(buckets, lock, "auth", "10.0.0.1", 3))

    assert results[:3] == [None, None, None]
    assert 1 <= results[3] <= rate_limit.WINDOW_SECONDS
    assert replica_a[0] == {} and replica_b[0] == {}
    assert set(redis.ttls.values()) == {rate_limit.WINDOW_SECONDS + 1}
    assert all(key.startswith("ratelimit:auth:10.0.0.1:") for key in redis.values)


async def test_redis_limit_keeps_clients_and_scopes_apart(monkeypatch) -> None:
    redis = CounterRedis()
    monkeypatch.setattr(rate_limit, "get_cache_client", lambda: redis)
    buckets, lock = {}, asyncio.Lock()

    assert await rate_limit.check_rate_limit(buckets, lock, "upload", "1.1.1.1", 1) is None
    assert await rate_limit.check_rate_limit(buckets, lock, "upload", "2.2.2.2", 1) is None
    assert await rate_limit.check_rate_limit(buckets, lock, "api", "1.1.1.1", 1) is None
    assert await rate_limit.check_rate_limit(buckets, lock, "upload", "1.1.1.1", 1) is not None


async def test_falls_back_to_process_limit_when_redis_fails(monkeypatch) -> None:
    monkeypatch.setattr(rate_limit, "get_cache_client", lambda: BrokenRedis())
    buckets, lock = {}, asyncio.Lock()

    first = await rate_limit.check_rate_limit(buckets, lock, "auth", "10.0.0.2", 1)
    second = await rate_limit.check_rate_limit(buckets, lock, "auth", "10.0.0.2", 1)

    assert first is None
    assert second is not None
    assert len(buckets[("10.0.0.2", "auth")]) == 1
