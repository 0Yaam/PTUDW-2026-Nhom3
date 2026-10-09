"""Delete orphaned image objects without holding up recipe requests."""

import asyncio
from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import select, update

from ..db import SessionFactory
from .model import FileDeletionJob
from .service import FileStorage, S3FileStorage

logger = structlog.get_logger()
RETRY_DELAYS = (60, 300, 1800)
MAX_ATTEMPTS = len(RETRY_DELAYS) + 1


async def process_due_job(
    *, storage: FileStorage | None = None, now: datetime | None = None
) -> bool:
    """Process one due object. Row locking prevents concurrent workers claiming it."""
    now = now or datetime.now(UTC)
    async with SessionFactory() as session:
        async with session.begin():
            query = (
                select(FileDeletionJob)
                .where(
                    FileDeletionJob.status == "Pending",
                    FileDeletionJob.next_attempt_at <= now,
                )
                .order_by(FileDeletionJob.next_attempt_at, FileDeletionJob.id)
                .limit(1)
            )
            if session.bind.dialect.name == "postgresql":
                query = query.with_for_update(skip_locked=True)
            job = await session.scalar(query)
            if job is None:
                return False
            try:
                store = storage or S3FileStorage()
                if job.variant:
                    await store.delete_variant(job.recipe_id, job.image_id, job.variant)
                elif job.original_url:
                    await store.delete(job.original_url)
            except Exception as error:
                job.attempts += 1
                job.last_error = type(error).__name__
                if job.attempts >= MAX_ATTEMPTS:
                    job.status = "Failed"
                    logger.error(
                        "file_cleanup_failed", job_id=str(job.id), error_type=job.last_error
                    )
                else:
                    job.next_attempt_at = now + timedelta(seconds=RETRY_DELAYS[job.attempts - 1])
                    logger.warning(
                        "file_cleanup_retry", job_id=str(job.id), error_type=job.last_error
                    )
            else:
                job.status = "Done"
                job.attempts += 1
                job.finished_at = now
                job.last_error = None
                logger.info("file_cleanup_done", job_id=str(job.id))
            return True


async def retry_failed_jobs() -> int:
    """Operator recovery after storage credentials or availability are restored."""
    async with SessionFactory() as session:
        async with session.begin():
            result = await session.execute(
                update(FileDeletionJob)
                .where(FileDeletionJob.status == "Failed")
                .values(status="Pending", attempts=0, next_attempt_at=datetime.now(UTC))
            )
            return result.rowcount


async def run_worker() -> None:
    logger.info("file_cleanup_worker_started")
    while True:
        try:
            if not await process_due_job():
                await asyncio.sleep(5)
        except Exception:
            logger.exception("file_cleanup_worker_error")
            await asyncio.sleep(5)


if __name__ == "__main__":
    import sys

    if "--retry-failed" in sys.argv:
        print(asyncio.run(retry_failed_jobs()))
    else:
        asyncio.run(run_worker())
