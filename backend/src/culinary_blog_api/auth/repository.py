import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from .model import RefreshToken, User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, user_id: uuid.UUID) -> User | None:
        return await self.session.get(User, user_id)

    async def get_by_email(self, email: str) -> User | None:
        return await self.session.scalar(select(User).where(User.email == email))

    async def get_by_user_name(self, user_name: str) -> User | None:
        return await self.session.scalar(select(User).where(User.user_name == user_name))

    async def get_by_email_or_user_name(self, email: str, user_name: str) -> User | None:
        return await self.session.scalar(
            select(User).where(or_(User.email == email, User.user_name == user_name))
        )

    async def get_by_user_name_except(
        self, user_name: str, user_id: uuid.UUID
    ) -> User | None:
        return await self.session.scalar(
            select(User).where(User.user_name == user_name, User.id != user_id)
        )

    def add(self, user: User) -> None:
        self.session.add(user)


class RefreshTokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_hash(
        self, token_hash: str, *, for_update: bool = False
    ) -> RefreshToken | None:
        query = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        if for_update:
            query = query.with_for_update()
        return await self.session.scalar(query)

    def add(self, token: RefreshToken) -> None:
        self.session.add(token)
