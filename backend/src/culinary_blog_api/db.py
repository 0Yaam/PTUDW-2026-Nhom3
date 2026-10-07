import time
from collections.abc import AsyncIterator

import structlog
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from .config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()
engine_options = {"pool_pre_ping": True}
if settings.database_url.startswith("postgresql"):
    engine_options.update(
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
    )
engine = create_async_engine(settings.database_url, **engine_options)
SessionFactory = async_sessionmaker(engine, expire_on_commit=False)
logger = structlog.get_logger()


@event.listens_for(engine.sync_engine, "before_cursor_execute")
def _start_query(_conn, _cursor, _statement, _parameters, _context, _executemany) -> None:
    _context._culinary_started = time.perf_counter()


@event.listens_for(engine.sync_engine, "after_cursor_execute")
def _finish_query(_conn, _cursor, statement, _parameters, context, _executemany) -> None:
    elapsed_ms = (time.perf_counter() - context._culinary_started) * 1000
    if elapsed_ms > 100:
        logger.warning(
            "slow_database_query", elapsed_ms=round(elapsed_ms, 2),
            operation=statement.lstrip().split(None, 1)[0].upper(),
        )


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionFactory() as session:
        yield session
