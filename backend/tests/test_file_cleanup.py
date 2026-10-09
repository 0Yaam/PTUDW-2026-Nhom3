"""Durable object cleanup retries and operator recovery."""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from culinary_blog_api.db import SessionFactory
from culinary_blog_api.storage.model import FileDeletionJob
from culinary_blog_api.storage.worker import process_due_job, retry_failed_jobs


class OfflineStorage:
    async def delete(self, _url: str) -> None:
        raise OSError("storage offline")


async def test_cleanup_retries_then_can_be_requeued() -> None:
    async with SessionFactory() as session:
        session.add(FileDeletionJob(
            original_url="http://storage.test/recipes/orphan.png",
            recipe_id=uuid.uuid4(), image_id=uuid.uuid4(),
        ))
        await session.commit()

    clock = datetime.now(UTC) + timedelta(seconds=1)
    for delay in (60, 300, 1800):
        assert await process_due_job(storage=OfflineStorage(), now=clock)
        clock += timedelta(seconds=delay)
    assert await process_due_job(storage=OfflineStorage(), now=clock)
    async with SessionFactory() as session:
        job = await session.scalar(select(FileDeletionJob))
        assert job.status == "Failed" and job.attempts == 4
        assert job.last_error == "OSError"
    assert await retry_failed_jobs() == 1
    async with SessionFactory() as session:
        job = await session.scalar(select(FileDeletionJob))
        assert job.status == "Pending" and job.attempts == 0
