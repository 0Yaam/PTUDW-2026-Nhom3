"""Run durable welcome-email jobs outside the HTTP request process.

PostgreSQL row locks let multiple workers claim different due jobs. A worker
crash rolls back its claim so another worker can try again.
"""

import asyncio
import hashlib
import html
import smtplib
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage
from email.utils import parseaddr

import structlog
from sqlalchemy import select, update

from ..auth.model import PasswordResetToken
from ..auth.security import create_password_reset_token
from ..config import Settings, get_settings
from ..db import SessionFactory
from .model import PasswordResetEmailJob, WelcomeEmailJob

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
    # Stable per account: providers that deduplicate Message-ID can suppress a
    # replay after SMTP accepted the email but the worker crashed before commit.
    digest = hashlib.sha256(recipient.lower().encode()).hexdigest()[:32]
    sender_domain = parseaddr(settings.smtp_from)[1].rpartition("@")[2] or "culinary-blog.local"
    message["Message-ID"] = f"<welcome-{digest}@{sender_domain}>"
    message.set_content(f"Hello {full_name}, welcome to Culinary Blog! {settings.app_public_url}")
    message.add_alternative(
        f"<p>Hello {name}, welcome to Culinary Blog!</p>"
        f'<p><a href="{app_url}">Explore recipes</a></p>',
        subtype="html",
    )
    if settings.smtp_ssl and settings.smtp_starttls:
        raise ValueError("SMTP_SSL and SMTP_STARTTLS are mutually exclusive")
    connection = smtplib.SMTP_SSL if settings.smtp_ssl else smtplib.SMTP
    with connection(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
        if settings.smtp_starttls:
            smtp.starttls()
        if settings.smtp_username:
            smtp.login(settings.smtp_username, settings.smtp_password.get_secret_value())
        smtp.send_message(message)


def send_password_reset_email(
    recipient: str, full_name: str, token: str, settings: Settings
) -> None:
    if not settings.smtp_host:
        raise RuntimeError("SMTP_HOST is not configured")
    name = html.escape(full_name)
    reset_url = f"{settings.app_public_url.rstrip('/')}/reset-password?token={token}"
    safe_reset_url = html.escape(reset_url, quote=True)
    message = EmailMessage()
    message["Subject"] = "Reset your Culinary Blog password"
    message["From"] = settings.smtp_from
    message["To"] = recipient
    digest = hashlib.sha256(token.encode()).hexdigest()[:32]
    sender_domain = parseaddr(settings.smtp_from)[1].rpartition("@")[2] or "culinary-blog.local"
    message["Message-ID"] = f"<password-reset-{digest}@{sender_domain}>"
    message.set_content(f"Hello {full_name}, reset your Culinary Blog password: {reset_url}")
    message.add_alternative(
        f"<p>Hello {name},</p>"
        "<p>Use this one-time link to reset your Culinary Blog password. "
        "It expires in 30 minutes.</p>"
        f'<p><a href="{safe_reset_url}">Reset password</a></p>',
        subtype="html",
    )
    if settings.smtp_ssl and settings.smtp_starttls:
        raise ValueError("SMTP_SSL and SMTP_STARTTLS are mutually exclusive")
    connection = smtplib.SMTP_SSL if settings.smtp_ssl else smtplib.SMTP
    with connection(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
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


async def process_due_password_reset_job(
    *,
    sender: Callable[[str, str, str, Settings], None] = send_password_reset_email,
    now: datetime | None = None,
) -> bool:
    now = now or datetime.now(UTC)
    async with SessionFactory() as session:
        async with session.begin():
            query = (
                select(PasswordResetEmailJob, PasswordResetToken)
                .join(
                    PasswordResetToken,
                    PasswordResetToken.id == PasswordResetEmailJob.reset_token_id,
                )
                .where(
                    PasswordResetEmailJob.status == "Pending",
                    PasswordResetEmailJob.next_attempt_at <= now,
                )
                .order_by(
                    PasswordResetEmailJob.next_attempt_at,
                    PasswordResetEmailJob.id,
                )
                .limit(1)
            )
            if session.bind.dialect.name == "postgresql":
                query = query.with_for_update(skip_locked=True)
            row = (await session.execute(query)).first()
            if row is None:
                return False
            job, reset_token = row
            expires_at = job.expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=UTC)
            if expires_at <= now or reset_token.used_at is not None:
                job.status = "Failed"
                job.last_error = "ExpiredOrUsed"
                return True
            token, _, _ = create_password_reset_token(reset_token.user_id, job.token_id, expires_at)
            try:
                await asyncio.to_thread(sender, job.recipient, job.full_name, token, get_settings())
            except Exception as error:
                job.attempts += 1
                job.last_error = type(error).__name__
                if job.attempts >= MAX_ATTEMPTS:
                    job.status = "Failed"
                    logger.error(
                        "password_reset_email_failed_permanently",
                        job_id=str(job.id),
                        attempts=job.attempts,
                        error_type=job.last_error,
                    )
                else:
                    job.next_attempt_at = now + timedelta(seconds=RETRY_DELAYS[job.attempts - 1])
                    logger.warning(
                        "password_reset_email_retry_scheduled",
                        job_id=str(job.id),
                        attempts=job.attempts,
                        error_type=job.last_error,
                    )
            else:
                job.status = "Sent"
                job.attempts += 1
                job.sent_at = now
                job.last_error = None
                logger.info("password_reset_email_sent", job_id=str(job.id))
            return True


async def retry_failed_jobs() -> int:
    """Requeue failed messages after an operator fixes delivery configuration."""
    async with SessionFactory() as session:
        async with session.begin():
            result = await session.execute(
                update(WelcomeEmailJob)
                .where(WelcomeEmailJob.status == "Failed")
                .values(status="Pending", attempts=0, next_attempt_at=datetime.now(UTC))
            )
            return result.rowcount


async def run_worker() -> None:
    """Poll the shared database. Each worker instance is independent."""
    logger.info("welcome_email_worker_started")
    while True:
        try:
            processed = await process_due_job()
            if not processed:
                processed = await process_due_password_reset_job()
        except Exception:
            logger.exception("welcome_email_worker_error")
            await asyncio.sleep(5)
        else:
            if not processed:
                await asyncio.sleep(5)


if __name__ == "__main__":
    import sys

    if "--retry-failed" in sys.argv:
        print(asyncio.run(retry_failed_jobs()))
    else:
        asyncio.run(run_worker())
