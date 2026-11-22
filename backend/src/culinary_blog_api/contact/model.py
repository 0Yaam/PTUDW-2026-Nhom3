import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


class ContactMessage(Base):
    """A submitted message and its durable email-delivery state."""

    __tablename__ = "contact_messages"
    __table_args__ = (Index("ix_contact_messages_due", "status", "next_attempt_at"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    full_name: Mapped[str] = mapped_column(String(150))
    email: Mapped[str] = mapped_column(String(320))
    message: Mapped[str] = mapped_column(Text())
    status: Mapped[str] = mapped_column(String(16), default="Pending", server_default="Pending")
    attempts: Mapped[int] = mapped_column(Integer(), default=0, server_default="0")
    next_attempt_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_error: Mapped[str | None] = mapped_column(String(120))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
