import pytest

from culinary_blog_api.auth.model import User
from culinary_blog_api.auth.security import hash_password
from culinary_blog_api.db import SessionFactory
from culinary_blog_api.unit_of_work import UnitOfWork


def user(email: str, user_name: str) -> User:
    return User(
        full_name="Unit of Work Test",
        email=email,
        user_name=user_name,
        password_hash=hash_password("StrongPass1!"),
        role="Author",
    )


async def test_unit_of_work_commits_and_rolls_back() -> None:
    async with SessionFactory() as session:
        unit_of_work = UnitOfWork(session)
        unit_of_work.users.add(user("commit@example.com", "commit_user"))
        await unit_of_work.commit()

    async with SessionFactory() as session:
        unit_of_work = UnitOfWork(session)
        assert await unit_of_work.users.get_by_email("commit@example.com") is not None

        with pytest.raises(RuntimeError):
            async with unit_of_work:
                unit_of_work.users.add(user("rollback@example.com", "rollback_user"))
                await unit_of_work.flush()
                raise RuntimeError("force rollback")

    async with SessionFactory() as session:
        unit_of_work = UnitOfWork(session)
        assert await unit_of_work.users.get_by_email("rollback@example.com") is None
