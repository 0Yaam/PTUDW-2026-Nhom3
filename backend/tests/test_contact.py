import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from culinary_blog_api.config import Settings
from culinary_blog_api.contact.model import ContactMessage
from culinary_blog_api.db import SessionFactory
from culinary_blog_api.jobs import worker
from culinary_blog_api.jobs.worker import process_due_contact_job

PAYLOAD = {
    "fullName": "  Nguyen Ngoc Han  ",
    "email": "  HAN@example.com ",
    "message": "Toi muon trao doi ve mot cong thuc moi.",
}


async def get_contact() -> ContactMessage:
    async with SessionFactory() as session:
        contact = await session.scalar(select(ContactMessage))
        assert contact is not None
        return contact


async def test_contact_submission_is_stored_and_queued(client) -> None:
    response = await client.post("/api/v1/contact", json=PAYLOAD)

    assert response.status_code == 202
    assert response.json()["status"] == "accepted"
    contact = await get_contact()
    assert contact.full_name == "Nguyen Ngoc Han"
    assert contact.email == "han@example.com"
    assert contact.message == PAYLOAD["message"]
    assert contact.status == "Pending"
    assert contact.attempts == 0


async def test_contact_rejects_invalid_input_as_problem_details(client) -> None:
    response = await client.post(
        "/api/v1/contact",
        json={"fullName": "Han", "email": "not-an-email", "message": "too short"},
    )

    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["type"] == "VALIDATION_ERROR"
    async with SessionFactory() as session:
        assert await session.scalar(select(func.count()).select_from(ContactMessage)) == 0


async def test_contact_endpoint_is_limited_to_five_requests_per_minute(client) -> None:
    responses = [await client.post("/api/v1/contact", json=PAYLOAD) for _ in range(6)]

    assert [response.status_code for response in responses] == [202, 202, 202, 202, 202, 429]
    assert responses[-1].headers["retry-after"]


async def test_worker_delivers_contact_message(client) -> None:
    response = await client.post("/api/v1/contact", json=PAYLOAD)
    assert response.status_code == 202
    sent: list[tuple[uuid.UUID, str, str, str]] = []

    def capture(
        contact_id: uuid.UUID,
        reply_to: str,
        full_name: str,
        content: str,
        _settings: Settings,
    ) -> None:
        sent.append((contact_id, reply_to, full_name, content))

    assert await process_due_contact_job(
        sender=capture,
        now=datetime.now(UTC) + timedelta(seconds=1),
    )
    contact = await get_contact()
    assert sent == [(contact.id, "han@example.com", "Nguyen Ngoc Han", PAYLOAD["message"])]
    assert contact.status == "Sent"
    assert contact.attempts == 1
    assert contact.sent_at is not None
    assert not await process_due_contact_job(sender=capture)


def test_contact_email_escapes_html_and_sets_reply_to(monkeypatch) -> None:
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
    contact_id = uuid.uuid4()
    settings = Settings(
        _env_file=None,
        smtp_host="smtp.test",
        contact_recipient="owner@example.com",
    )

    worker.send_contact_email(
        contact_id,
        "han@example.com",
        "<Han>",
        "Hello <script>alert(1)</script>",
        settings,
    )

    assert len(sent) == 1
    assert sent[0]["To"] == "owner@example.com"
    assert sent[0]["Reply-To"] == "han@example.com"
    assert sent[0]["Message-ID"].startswith(f"<contact-{contact_id}@")
    html_body = sent[0].get_body(preferencelist=("html",)).get_content()
    assert "&lt;Han&gt;" in html_body
    assert "&lt;script&gt;" in html_body
    assert "<script>" not in html_body
