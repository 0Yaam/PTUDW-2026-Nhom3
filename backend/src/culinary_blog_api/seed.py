import asyncio

from sqlalchemy import select

from .categories import Category
from .db import SessionFactory

SEED_CATEGORIES = [
    ("Vietnamese Food", "vietnamese-food", "Home recipes from across Vietnam.", 1),
    ("Breakfast", "breakfast", "Simple meals for a good start to the day.", 2),
    ("Plant-Based", "plant-based", "Fresh recipes with vegetables and grains.", 3),
    ("Baking and Desserts", "baking-and-desserts", "Sweet food to bake and share.", 4),
]


async def seed() -> None:
    async with SessionFactory() as session:
        for name, slug, description, order_index in SEED_CATEGORIES:
            existing = await session.scalar(select(Category).where(Category.slug == slug))
            if existing is None:
                session.add(
                    Category(
                        name=name,
                        slug=slug,
                        description=description,
                        order_index=order_index,
                    )
                )
            # Seed data is a starting point, not the source of truth after an Admin edits it.
        await session.commit()


def main() -> None:
    asyncio.run(seed())


if __name__ == "__main__":
    main()
