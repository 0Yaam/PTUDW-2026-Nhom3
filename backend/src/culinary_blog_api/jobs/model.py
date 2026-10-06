"""Database-backed outbox for welcome mail.

Rows are committed with registration, then claimed by independent workers.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


class WelcomeEmailJob(Base):
    __tablename__ = "welcome_email_jobs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )
    recipient: Mapped[str] = mapped_column(String(320))
    full_name: Mapped[str] = mapped_column(String(150))
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

    __table_args__ = (Index("ix_welcome_email_jobs_due", "status", "next_attempt_at"),)


# Register the FK target after defining the job so auth.service can import this
# model while auth.__init__ loads its router in a standalone worker process.
from ..auth.model import User  # noqa: E402, F401
