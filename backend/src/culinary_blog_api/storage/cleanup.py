"""Queue one idempotent delete per object in the caller's database transaction."""

from sqlalchemy.ext.asyncio import AsyncSession

from ..recipes.model import RecipeImage
from .model import FileDeletionJob


def queue_image_cleanup(session: AsyncSession, image: RecipeImage) -> None:
    session.add_all(
        [
            FileDeletionJob(
                original_url=image.original_url, recipe_id=image.recipe_id, image_id=image.id
            ),
            FileDeletionJob(recipe_id=image.recipe_id, image_id=image.id, variant="medium"),
            FileDeletionJob(recipe_id=image.recipe_id, image_id=image.id, variant="thumbnail"),
        ]
    )
