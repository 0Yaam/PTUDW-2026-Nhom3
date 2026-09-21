import os

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["FRONTEND_ORIGIN"] = "http://localhost:3000"

from collections.abc import AsyncIterator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from culinary_blog_api.db import Base, engine
from culinary_blog_api.main import app


@pytest_asyncio.fixture(autouse=True)
async def database() -> AsyncIterator[None]:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as test_client:
        yield test_client
