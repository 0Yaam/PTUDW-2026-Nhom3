from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from culinary_blog_api.auth import PasswordResetToken, RefreshToken, User
from culinary_blog_api.auth import service as auth_service
from culinary_blog_api.auth.security import (
    create_password_reset_token,
    hash_password_reset_token_id,
    read_password_reset_token,
)
from culinary_blog_api.db import SessionFactory
from culinary_blog_api.jobs.model import PasswordResetEmailJob

REGISTER_PAYLOAD = {
    "fullName": "Nguyen Ngoc Truong Dan",
    "email": "dan@example.com",
    "userName": "truongdan",
    "password": "StrongPass1!",
}


async def test_google_login_creates_author_and_reuses_verified_email(client, monkeypatch) -> None:
    async def fake_profile(_id_token: str) -> dict[str, str]:
        return {
            "email": "google@example.com",
            "name": "Google User",
            "picture": "https://example.com/avatar.jpg",
        }

    monkeypatch.setattr(auth_service, "fetch_google_profile", fake_profile)

    first = await client.post("/api/v1/auth/google", json={"idToken": "valid-token"})
    second = await client.post("/api/v1/auth/google", json={"idToken": "valid-token"})

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["user"]["roles"] == ["Author"]
    assert first.json()["user"]["id"] == second.json()["user"]["id"]

    async with SessionFactory() as session:
        users = (
            await session.scalars(select(User).where(User.email == "google@example.com"))
        ).all()
        assert len(users) == 1


async def test_register_creates_author_and_tokens(client) -> None:
    response = await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)

    assert response.status_code == 201
    body = response.json()
    assert body["user"]["roles"] == ["Author"]
    assert body["user"]["email"] == "dan@example.com"
    assert body["accessToken"].count(".") == 2
    assert body["refreshToken"]
    assert "password" not in str(body).lower()

    async with SessionFactory() as session:
        user = await session.scalar(select(User).where(User.email == "dan@example.com"))
        refresh_token = await session.scalar(select(RefreshToken))
        assert user is not None
        assert user.password_hash != REGISTER_PAYLOAD["password"]
        assert user.password_hash.startswith("pbkdf2_sha512$210000$")
        assert refresh_token is not None
        assert refresh_token.token_hash != body["refreshToken"]


async def test_login_returns_new_tokens(client) -> None:
    await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": REGISTER_PAYLOAD["email"], "password": REGISTER_PAYLOAD["password"]},
    )

    assert response.status_code == 200
    assert response.json()["user"]["userName"] == "truongdan"


async def test_refresh_rotates_token_and_logout_revokes_it(client) -> None:
    registered = await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    first = registered.json()

    refreshed = await client.post(
        "/api/v1/auth/refresh",
        json={"refreshToken": first["refreshToken"]},
    )
    assert refreshed.status_code == 200
    second = refreshed.json()
    assert second["accessToken"] != first["accessToken"]
    assert second["refreshToken"] != first["refreshToken"]

    reused = await client.post(
        "/api/v1/auth/refresh",
        json={"refreshToken": first["refreshToken"]},
    )
    assert reused.status_code == 401
    assert reused.json()["type"] == "INVALID_REFRESH_TOKEN"

    logged_out = await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {second['accessToken']}"},
        json={"refreshToken": second["refreshToken"]},
    )
    assert logged_out.status_code == 204

    after_logout = await client.post(
        "/api/v1/auth/refresh",
        json={"refreshToken": second["refreshToken"]},
    )
    assert after_logout.status_code == 401


async def test_logout_is_idempotent_for_unknown_refresh_token(client) -> None:
    registered = await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    body = registered.json()

    response = await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {body['accessToken']}"},
        json={"refreshToken": "unknown-token"},
    )
    assert response.status_code == 204


async def test_duplicate_registration_returns_problem_details(client) -> None:
    await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)

    response = await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)

    assert response.status_code == 409
    assert response.json() == {
        "type": "ACCOUNT_ALREADY_EXISTS",
        "title": "Conflict",
        "status": 409,
        "detail": "Email or user name is already registered.",
    }


async def test_invalid_registration_returns_validation_problem(client) -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={**REGISTER_PAYLOAD, "password": "weak"},
    )

    assert response.status_code == 422
    assert response.json()["type"] == "VALIDATION_ERROR"
    assert "password" in response.json()["errors"]


async def test_login_does_not_reveal_whether_account_exists(client) -> None:
    await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)

    wrong_password = await client.post(
        "/api/v1/auth/login",
        json={"email": REGISTER_PAYLOAD["email"], "password": "WrongPass1!"},
    )
    missing_account = await client.post(
        "/api/v1/auth/login",
        json={"email": "missing@example.com", "password": "WrongPass1!"},
    )

    assert wrong_password.status_code == missing_account.status_code == 401
    assert wrong_password.json() == missing_account.json()


async def test_account_locks_after_five_failed_attempts(client) -> None:
    await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)

    for _ in range(4):
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": REGISTER_PAYLOAD["email"], "password": "WrongPass1!"},
        )
        assert response.status_code == 401

    locked = await client.post(
        "/api/v1/auth/login",
        json={"email": REGISTER_PAYLOAD["email"], "password": "WrongPass1!"},
    )
    assert locked.status_code == 423
    assert locked.json()["type"] == "ACCOUNT_LOCKED"


async def test_change_password_revokes_existing_sessions(client) -> None:
    registered = await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    session = registered.json()

    wrong = await client.post(
        "/api/v1/auth/change-password",
        headers={"Authorization": f"Bearer {session['accessToken']}"},
        json={"currentPassword": "WrongPass1!", "newPassword": "NewStrongPass2!"},
    )
    assert wrong.status_code == 400
    assert wrong.json()["type"] == "CURRENT_PASSWORD_INCORRECT"

    changed = await client.post(
        "/api/v1/auth/change-password",
        headers={"Authorization": f"Bearer {session['accessToken']}"},
        json={
            "currentPassword": REGISTER_PAYLOAD["password"],
            "newPassword": "NewStrongPass2!",
        },
    )
    assert changed.status_code == 204

    old_access = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {session['accessToken']}"},
    )
    old_refresh = await client.post(
        "/api/v1/auth/refresh",
        json={"refreshToken": session["refreshToken"]},
    )
    old_login = await client.post(
        "/api/v1/auth/login",
        json={"email": REGISTER_PAYLOAD["email"], "password": REGISTER_PAYLOAD["password"]},
    )
    new_login = await client.post(
        "/api/v1/auth/login",
        json={"email": REGISTER_PAYLOAD["email"], "password": "NewStrongPass2!"},
    )

    assert old_access.status_code == 401
    assert old_refresh.status_code == 401
    assert old_login.status_code == 401
    assert new_login.status_code == 200


async def test_forgot_password_is_generic_and_queues_hashed_one_time_token(client) -> None:
    await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)

    existing = await client.post(
        "/api/v1/auth/forgot-password", json={"email": REGISTER_PAYLOAD["email"]}
    )
    missing = await client.post(
        "/api/v1/auth/forgot-password", json={"email": "missing@example.com"}
    )

    assert existing.status_code == missing.status_code == 202
    assert existing.content == missing.content == b""
    async with SessionFactory() as session:
        reset_token = await session.scalar(select(PasswordResetToken))
        email_job = await session.scalar(select(PasswordResetEmailJob))
        assert reset_token is not None
        assert email_job is not None
        assert reset_token.token_hash == hash_password_reset_token_id(email_job.token_id)
        assert reset_token.token_hash != email_job.token_id
        assert await session.scalar(select(func.count(PasswordResetToken.id))) == 1


async def test_reset_password_is_single_use_and_revokes_existing_sessions(client) -> None:
    registered = await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    old_session = registered.json()
    await client.post("/api/v1/auth/forgot-password", json={"email": REGISTER_PAYLOAD["email"]})

    async with SessionFactory() as session:
        reset_token = await session.scalar(select(PasswordResetToken))
        email_job = await session.scalar(select(PasswordResetEmailJob))
        assert reset_token is not None
        assert email_job is not None
        token, _, _ = create_password_reset_token(
            reset_token.user_id, email_job.token_id, email_job.expires_at
        )
        claims = read_password_reset_token(token)
        assert claims is not None
        assert claims.user_id == reset_token.user_id
        assert reset_token.token_hash == hash_password_reset_token_id(claims.token_id)

    reset = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "newPassword": "ResetStrongPass3!"},
    )
    reused = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "newPassword": "AnotherStrongPass4!"},
    )
    old_access = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {old_session['accessToken']}"},
    )
    old_refresh = await client.post(
        "/api/v1/auth/refresh",
        json={"refreshToken": old_session["refreshToken"]},
    )
    new_login = await client.post(
        "/api/v1/auth/login",
        json={"email": REGISTER_PAYLOAD["email"], "password": "ResetStrongPass3!"},
    )

    assert reset.status_code == 204, reset.json()
    assert reused.status_code == 400
    assert reused.json()["type"] == "INVALID_PASSWORD_RESET_TOKEN"
    assert old_access.status_code == 401
    assert old_refresh.status_code == 401
    assert new_login.status_code == 200


async def test_expired_password_reset_token_is_rejected(client) -> None:
    await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    async with SessionFactory() as session:
        user = await session.scalar(select(User).where(User.email == REGISTER_PAYLOAD["email"]))
        assert user is not None
        expires_at = datetime.now(UTC) - timedelta(minutes=1)
        token, token_id, _ = create_password_reset_token(user.id, expires_at=expires_at)
        session.add(
            PasswordResetToken(
                user_id=user.id,
                token_hash=hash_password_reset_token_id(token_id),
                expires_at=expires_at,
            )
        )
        await session.commit()

    response = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "newPassword": "ResetStrongPass3!"},
    )

    assert response.status_code == 400
    assert response.json()["type"] == "INVALID_PASSWORD_RESET_TOKEN"
