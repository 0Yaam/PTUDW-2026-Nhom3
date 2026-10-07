"""Resize uploaded recipe images outside the HTTP request process."""

import asyncio
from datetime import UTC, datetime, timedelta
from io import BytesIO

import structlog
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import or_, select

from ..db import SessionFactory
from ..storage import FileStorage, S3FileStorage
from .cache import invalidate_recipe_caches
from .model import Recipe, RecipeImage, RecipeImageResizeJob

logger = structlog.get_logger()
RETRY_DELAYS = (60, 300, 1800)
MAX_ATTEMPTS = len(RETRY_DELAYS) + 1
LEASE = timedelta(minutes=5)
Image.MAX_IMAGE_PIXELS = 25_000_000


def render_variants(data: bytes) -> dict[str, bytes]:
    """Apply EXIF orientation, center crop, and encode both exact-size WebP assets."""
    try:
        with Image.open(BytesIO(data)) as source:
            source.load()
            oriented = ImageOps.exif_transpose(source)
            mode = "RGBA" if "A" in oriented.getbands() else "RGB"
            prepared = oriented.convert(mode)
            result: dict[str, bytes] = {}
            for name, dimensions in (("medium", (800, 600)), ("thumbnail", (300, 300))):
                resized = ImageOps.fit(prepared, dimensions, method=Image.Resampling.LANCZOS)
                output = BytesIO()
                resized.save(output, format="WEBP", quality=82, method=4)
                result[name] = output.getvalue()
            return result
    except (OSError, ValueError, UnidentifiedImageError, Image.DecompressionBombError) as error:
        raise ValueError("Stored recipe image cannot be resized.") from error


async def _claim(now: datetime) -> object | None:
    async with SessionFactory() as session:
        async with session.begin():
            query = (
                select(RecipeImageResizeJob)
                .where(
                    or_(
                        RecipeImageResizeJob.status == "Pending",
                        RecipeImageResizeJob.status == "Processing",
                    ),
                    RecipeImageResizeJob.next_attempt_at <= now,
                )
                .order_by(RecipeImageResizeJob.next_attempt_at, RecipeImageResizeJob.id)
                .limit(1)
            )
            if session.bind.dialect.name == "postgresql":
                query = query.with_for_update(skip_locked=True)
            job = await session.scalar(query)
            if job is None:
                return None
            if job.attempts >= MAX_ATTEMPTS:
                job.status = "Failed"
                return None
            job.status = "Processing"
            job.attempts += 1
            job.next_attempt_at = now + LEASE
            return job.id


async def _process(job_id: object, storage: FileStorage, now: datetime) -> None:
    async with SessionFactory() as session:
        async with session.begin():
            image_id = await session.scalar(
                select(RecipeImageResizeJob.image_id).where(RecipeImageResizeJob.id == job_id)
            )
            if image_id is None:
                return  # An image deletion cascaded to its queued job.
            recipe_id = await session.scalar(
                select(RecipeImage.recipe_id).where(RecipeImage.id == image_id)
            )
            if recipe_id is None:
                return
            # Image delete locks the recipe first; the worker takes the same lock.
            await session.scalar(select(Recipe).where(Recipe.id == recipe_id).with_for_update())
            image = await session.get(RecipeImage, image_id)
            job = await session.get(RecipeImageResizeJob, job_id)
            if image is None or job is None or job.status != "Processing":
                return
            source = await storage.read(image.original_url)
            variants = await asyncio.to_thread(render_variants, source.data)
            medium_url = await storage.upload_variant(
                variants["medium"], recipe_id, image_id, "medium"
            )
            thumbnail_url = await storage.upload_variant(
                variants["thumbnail"], recipe_id, image_id, "thumbnail"
            )
            image.medium_url = medium_url
            image.thumbnail_url = thumbnail_url
            job.status = "Done"
            job.finished_at = now
            job.last_error = None
    await invalidate_recipe_caches()
    logger.info("recipe_image_resized", image_id=str(image_id), job_id=str(job_id))


async def _schedule_failure(job_id: object, error: Exception, now: datetime) -> None:
    async with SessionFactory() as session:
        async with session.begin():
            job = await session.get(RecipeImageResizeJob, job_id)
            if job is None or job.status != "Processing":
                return
            job.last_error = type(error).__name__
            if job.attempts >= MAX_ATTEMPTS:
                job.status = "Failed"
                logger.error(
                    "recipe_image_resize_failed", job_id=str(job_id), attempts=job.attempts,
                    error_type=job.last_error,
                )
            else:
                job.status = "Pending"
                job.next_attempt_at = now + timedelta(seconds=RETRY_DELAYS[job.attempts - 1])
                logger.warning(
                    "recipe_image_resize_retry", job_id=str(job_id), attempts=job.attempts,
                    error_type=job.last_error,
                )


async def process_due_job(
    *, storage: FileStorage | None = None, now: datetime | None = None
) -> bool:
    now = now or datetime.now(UTC)
    job_id = await _claim(now)
    if job_id is None:
        return False
    try:
        await _process(job_id, storage or S3FileStorage(), now)
    except Exception as error:
        await _schedule_failure(job_id, error, now)
    return True


async def run_worker() -> None:
    logger.info("recipe_image_worker_started")
    while True:
        try:
            processed = await process_due_job()
        except Exception:
            logger.exception("recipe_image_worker_error")
            await asyncio.sleep(5)
        else:
            if not processed:
                await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(run_worker())
