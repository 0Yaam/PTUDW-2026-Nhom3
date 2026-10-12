"""Registration outbox and worker retry behavior."""

import subprocess
import sys
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from culinary_blog_api.config import Settings
from culinary_blog_api.db import SessionFactory
from culinary_blog_api.jobs import worker
from culinary_blog_api.jobs.model import WelcomeEmailJob
from culinary_blog_api.jobs.worker import process_due_job

REGISTER_PAYLOAD = {
    "fullName": "Nguyen Ngoc Han",
    "email": "han@example.com",
    "userName": "nguyenhan",
    "password": "StrongPass1!",
}


def test_standalone_worker_loads_user_table_for_foreign_key() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from culinary_blog_api.jobs import worker; "
            "from culinary_blog_api.db import Base; "
            "assert 'users' in Base.metadata.tables",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


async def get_job() -> WelcomeEmailJob:
    async with SessionFactory() as session:
        job = await session.scalar(select(WelcomeEmailJob))
        assert job is not None
        return job


async def test_registration_queues_email_without_sending(client) -> None:
    response = await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)

    assert response.status_code == 201
    job = await get_job()
    assert job.recipient == REGISTER_PAYLOAD["email"]
    assert job.full_name == REGISTER_PAYLOAD["fullName"]
    assert job.status == "Pending"
    assert job.attempts == 0

    duplicate = await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    assert duplicate.status_code == 409
    async with SessionFactory() as session:
        assert len((await session.scalars(select(WelcomeEmailJob))).all()) == 1


async def test_worker_sends_welcome_email_after_registration(client) -> None:
    await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    sent: list[tuple[str, str]] = []

    def fake_sender(email, name, _settings) -> None:
        sent.append((email, name))

    assert await process_due_job(sender=fake_sender, now=datetime.now(UTC) + timedelta(seconds=1))
    assert sent == [(REGISTER_PAYLOAD["email"], REGISTER_PAYLOAD["fullName"])]
    assert (await get_job()).status == "Sent"
    assert not await process_due_job(sender=fake_sender)


async def test_worker_retries_three_times_then_marks_failed(client) -> None:
    await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)

    def failing_sender(_email, _name, _settings) -> None:
        raise OSError("SMTP offline")

    clock = datetime.now(UTC) + timedelta(seconds=1)
    for attempt, delay in enumerate((60, 300, 1800), start=1):
        assert await process_due_job(sender=failing_sender, now=clock)
        job = await get_job()
        assert job.status == "Pending"
        assert job.attempts == attempt
        assert job.last_error == "OSError"
        due = job.next_attempt_at.replace(tzinfo=UTC)
        assert due == clock + timedelta(seconds=delay)
        assert not await process_due_job(sender=failing_sender, now=clock)
        clock = due

    assert await process_due_job(sender=failing_sender, now=clock)
    job = await get_job()
    assert job.status == "Failed"
    assert job.attempts == 4
    assert not await process_due_job(sender=failing_sender, now=clock + timedelta(days=1))

    assert await worker.retry_failed_jobs() == 1
    assert (await get_job()).status == "Pending"


def test_html_welcome_email_escapes_name_and_links_to_app(monkeypatch) -> None:
    sent = []

    class FakeSMTP:
        def __init__(self, host, port, timeout) -> None:
            assert (host, port, timeout) == ("smtp.test", 1025, 10)

        def __enter__(self):
            return self

        def __exit__(self, *_args) -> None:
            pass

        def send_message(self, message) -> None:
            sent.append(message)

    monkeypatch.setattr(worker.smtplib, "SMTP", FakeSMTP)
    settings = Settings(
        _env_file=None,
        smtp_host="smtp.test",
        app_public_url="https://culinary.example/app",
    )

    worker.send_welcome_email("han@example.com", "<Han>", settings)
    worker.send_welcome_email("han@example.com", "<Han>", settings)

    assert len(sent) == 2
    assert sent[0]["To"] == "han@example.com"
    assert sent[0]["Message-ID"] == sent[1]["Message-ID"]
    html_body = sent[0].get_body(preferencelist=("html",)).get_content()
    assert "&lt;Han&gt;" in html_body
    assert "<Han>" not in html_body
    assert 'href="https://culinary.example/app"' in html_body


def test_smtp_ssl_uses_implicit_tls_and_rejects_mixed_modes(monkeypatch) -> None:
    used: list[str] = []

    class FakeSMTP:
        def __init__(self, *_args, **_kwargs) -> None:
            used.append("ssl")

        def __enter__(self):
            return self

        def __exit__(self, *_args) -> None:
            pass

        def send_message(self, _message) -> None:
            used.append("sent")

    monkeypatch.setattr(worker.smtplib, "SMTP_SSL", FakeSMTP)
    settings = Settings(_env_file=None, smtp_host="smtp.test", smtp_port=465, smtp_ssl=True)
    worker.send_welcome_email("han@example.com", "Han", settings)
    assert used == ["ssl", "sent"]

    import pytest

    with pytest.raises(ValueError, match="mutually exclusive"):
        worker.send_welcome_email(
            "han@example.com", "Han",
            Settings(_env_file=None, smtp_host="smtp.test", smtp_ssl=True, smtp_starttls=True),
        )
