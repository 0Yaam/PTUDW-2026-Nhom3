"""Run durable welcome-email jobs outside the HTTP request process.

PostgreSQL row locks let multiple workers claim different due jobs. A worker
crash rolls back its claim so another worker can try again.
"""

import asyncio
import html
import smtplib
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage

import structlog
from sqlalchemy import select

from ..config import Settings, get_settings
from ..db import SessionFactory
from .model import WelcomeEmailJob

logger = structlog.get_logger()
RETRY_DELAYS = (60, 300, 1800)
MAX_ATTEMPTS = len(RETRY_DELAYS) + 1


def send_welcome_email(recipient: str, full_name: str, settings: Settings) -> None:
    """Send one HTML welcome message; the worker owns retries and logging."""
    if not settings.smtp_host:
        raise RuntimeError("SMTP_HOST is not configured")
    name = html.escape(full_name)
    app_url = html.escape(settings.app_public_url.rstrip("/"), quote=True)
    message = EmailMessage()
    message["Subject"] = "Welcome to Culinary Blog"
    message["From"] = settings.smtp_from
    message["To"] = recipient
    message.set_content(f"Hello {full_name}, welcome to Culinary Blog! {settings.app_public_url}")
    message.add_alternative(
        f"<p>Hello {name}, welcome to Culinary Blog!</p>"
        f'<p><a href="{app_url}">Explore recipes</a></p>',
        subtype="html",
    )
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
        if settings.smtp_starttls:
            smtp.starttls()
        if settings.smtp_username:
            smtp.login(settings.smtp_username, settings.smtp_password.get_secret_value())
        smtp.send_message(message)


async def process_due_job(
    *,
    sender: Callable[[str, str, Settings], None] = send_welcome_email,
    now: datetime | None = None,
) -> bool:
    """Claim and process one job. Return False when no job is due."""
    now = now or datetime.now(UTC)
    async with SessionFactory() as session:
        async with session.begin():
            query = (
                select(WelcomeEmailJob)
                .where(
                    WelcomeEmailJob.status == "Pending",
                    WelcomeEmailJob.next_attempt_at <= now,
                )
                .order_by(WelcomeEmailJob.next_attempt_at, WelcomeEmailJob.id)
                .limit(1)
            )
            if session.bind.dialect.name == "postgresql":
                query = query.with_for_update(skip_locked=True)
            job = await session.scalar(query)
            if job is None:
                return False
            try:
                await asyncio.to_thread(sender, job.recipient, job.full_name, get_settings())
            except Exception as error:
                job.attempts += 1
                job.last_error = type(error).__name__
                if job.attempts >= MAX_ATTEMPTS:
                    job.status = "Failed"
                    logger.error(
                        "welcome_email_failed_permanently",
                        job_id=str(job.id),
                        attempts=job.attempts,
                        error_type=job.last_error,
                    )
                else:
                    job.next_attempt_at = now + timedelta(seconds=RETRY_DELAYS[job.attempts - 1])
                    logger.warning(
                        "welcome_email_retry_scheduled",
                        job_id=str(job.id),
                        attempts=job.attempts,
                        error_type=job.last_error,
                    )
            else:
                job.status = "Sent"
                job.attempts += 1
                job.sent_at = now
                job.last_error = None
                logger.info("welcome_email_sent", job_id=str(job.id))
            return True


async def run_worker() -> None:
    """Poll the shared database. Each worker instance is independent."""
    logger.info("welcome_email_worker_started")
    while True:
        try:
            processed = await process_due_job()
        except Exception:
            logger.exception("welcome_email_worker_error")
            await asyncio.sleep(5)
        else:
            if not processed:
                await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(run_worker())
