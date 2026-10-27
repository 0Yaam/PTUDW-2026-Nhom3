import uuid
from datetime import datetime

from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from .model import PasswordResetToken, RefreshToken, User


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

    async def get_by_user_name_except(self, user_name: str, user_id: uuid.UUID) -> User | None:
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

    async def revoke_all_for_user(self, user_id: uuid.UUID, revoked_at: datetime) -> None:
        await self.session.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=revoked_at)
        )


class PasswordResetTokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_hash(
        self, token_hash: str, *, for_update: bool = False
    ) -> PasswordResetToken | None:
        query = select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
        if for_update:
            query = query.with_for_update()
        return await self.session.scalar(query)

    async def invalidate_for_user(self, user_id: uuid.UUID, used_at: datetime) -> None:
        await self.session.execute(
            update(PasswordResetToken)
            .where(PasswordResetToken.user_id == user_id, PasswordResetToken.used_at.is_(None))
            .values(used_at=used_at)
        )

    def add(self, token: PasswordResetToken) -> None:
        self.session.add(token)
