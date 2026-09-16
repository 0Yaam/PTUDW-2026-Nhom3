from sqlalchemy import select

from culinary_blog_api.auth import RefreshToken, User
from culinary_blog_api.db import SessionFactory

REGISTER_PAYLOAD = {
    "fullName": "Nguyen Ngoc Truong Dan",
    "email": "dan@example.com",
    "userName": "truongdan",
    "password": "StrongPass1!",
}


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
