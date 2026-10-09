"""Durable requests to remove objects after recipe metadata is committed."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


class FileDeletionJob(Base):
    __tablename__ = "file_deletion_jobs"
    __table_args__ = (Index("ix_file_deletion_jobs_due", "status", "next_attempt_at"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    original_url: Mapped[str | None] = mapped_column(String(500))
    recipe_id: Mapped[uuid.UUID] = mapped_column()
    image_id: Mapped[uuid.UUID] = mapped_column()
    variant: Mapped[str | None] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16), default="Pending", server_default="Pending")
    attempts: Mapped[int] = mapped_column(Integer(), default=0, server_default="0")
    next_attempt_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_error: Mapped[str | None] = mapped_column(String(120))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
