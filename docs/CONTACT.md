# Contact form extension

This Part III extension lets any visitor send a message from `/contact`. The
request is validated and stored before the API responds, then the existing
email worker forwards it to the configured team inbox.

## Contract

`POST /api/v1/contact` accepts:

```json
{
  "fullName": "Nguyen Van A",
  "email": "a@example.com",
  "message": "I would like to discuss a recipe."
}
```

The endpoint returns `202 Accepted` with an opaque receipt ID. Validation
errors use RFC 7807. Names are limited to 150 characters, email addresses to
320 characters, and messages to 4,000 characters.

## Design

- `contact_messages` stores the submitted content and the email delivery
  state. The single committed row is also the durable outbox, so no message is
  lost between a database commit and an SMTP call.
- The shared email worker claims pending rows with `FOR UPDATE SKIP LOCKED` on
  PostgreSQL, retries transient failures, and records `Sent` or `Failed`.
- `CONTACT_RECIPIENT` chooses the destination inbox. Local Docker defaults to
  `owner@culinary.local`, visible in Mailpit.
- The browser never sends an email directly and the API never reflects the
  submitted message as HTML.

## Security

- The public endpoint is limited to five requests per client per minute.
- Pydantic rejects missing, oversized, malformed, or unexpected fields.
- SQLAlchemy uses parameterized statements.
- The worker creates a plain-text body and HTML-escapes the alternative body,
  preventing stored XSS in email clients.
- User input is placed only in `Reply-To`; it cannot choose the destination
  address, so the endpoint cannot be used as an open mail relay.
- The form warns visitors not to include passwords or sensitive information.

CAPTCHA, moderation, and an Admin inbox are reasonable upgrades if public
traffic or abuse grows.

## Verification

```powershell
uv run --directory backend pytest tests/test_contact.py
npm run lint --prefix frontend
npm run build --prefix frontend
docker compose exec api alembic current
```

After submitting the form, open Mailpit at `http://localhost:8025` and verify
the message addressed to `owner@culinary.local`.
