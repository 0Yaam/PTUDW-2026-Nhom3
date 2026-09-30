from sqlalchemy import select

from culinary_blog_api.auth import User
from culinary_blog_api.db import SessionFactory

REGISTER_PAYLOAD = {
    "fullName": "Nguyen Minh Anh",
    "email": "minhanh@example.com",
    "userName": "minhanh",
    "password": "StrongPass1!",
}
VALID_UPDATE = {
    "fullName": "Nguyễn Minh Anh",
    "userName": "minhanh_bep",
    "avatarUrl": "https://example.com/avatar.png",
}


async def sign_in(client) -> dict[str, str]:
    response = await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['accessToken']}"}


async def test_signed_in_user_reads_own_profile(client) -> None:
    headers = await sign_in(client)

    response = await client.get("/api/v1/auth/profile", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == REGISTER_PAYLOAD["email"]
    assert body["userName"] == REGISTER_PAYLOAD["userName"]
    assert body["fullName"] == REGISTER_PAYLOAD["fullName"]
    assert body["roles"] == ["Author"]


async def test_srs_me_aliases_read_and_update_profile(client) -> None:
    headers = await sign_in(client)

    read = await client.get("/api/v1/auth/me", headers=headers)
    updated = await client.patch("/api/v1/auth/me", json=VALID_UPDATE, headers=headers)

    assert read.status_code == 200
    assert updated.status_code == 200
    assert updated.json()["userName"] == VALID_UPDATE["userName"]


async def test_profile_never_returns_authentication_secrets(client) -> None:
    headers = await sign_in(client)

    read = await client.get("/api/v1/auth/profile", headers=headers)
    updated = await client.put("/api/v1/auth/profile", json=VALID_UPDATE, headers=headers)

    secret_fields = {
        "password",
        "passwordHash",
        "password_hash",
        "accessFailedCount",
        "access_failed_count",
        "lockoutUntil",
        "lockout_until",
    }
    for response in (read, updated):
        assert secret_fields.isdisjoint(response.json().keys())


async def test_profile_read_requires_authentication(client) -> None:
    response = await client.get("/api/v1/auth/profile")

    assert response.status_code == 401
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["type"] == "UNAUTHORIZED"


async def test_profile_update_requires_authentication(client) -> None:
    response = await client.put("/api/v1/auth/profile", json=VALID_UPDATE)

    assert response.status_code == 401
    assert response.json()["type"] == "UNAUTHORIZED"


async def test_deleted_account_cannot_read_its_profile(client) -> None:
    headers = await sign_in(client)
    async with SessionFactory() as session:
        user = await session.scalar(select(User).where(User.email == REGISTER_PAYLOAD["email"]))
        assert user is not None
        await session.delete(user)
        await session.commit()

    response = await client.get("/api/v1/auth/profile", headers=headers)

    assert response.status_code == 401
    assert response.json()["type"] == "UNAUTHORIZED"


async def test_update_persists_the_editable_fields(client) -> None:
    headers = await sign_in(client)

    response = await client.put("/api/v1/auth/profile", json=VALID_UPDATE, headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["fullName"] == VALID_UPDATE["fullName"]
    assert body["userName"] == VALID_UPDATE["userName"]
    assert body["avatarUrl"] == VALID_UPDATE["avatarUrl"]

    async with SessionFactory() as session:
        user = await session.scalar(select(User).where(User.email == REGISTER_PAYLOAD["email"]))
        assert user is not None
        assert user.full_name == VALID_UPDATE["fullName"]
        assert user.user_name == VALID_UPDATE["userName"]
        assert user.avatar_url == VALID_UPDATE["avatarUrl"]


async def test_update_keeps_email_and_role_out_of_reach(client) -> None:
    headers = await sign_in(client)

    response = await client.put(
        "/api/v1/auth/profile",
        json={**VALID_UPDATE, "email": "attacker@example.com", "roles": ["Admin"]},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["email"] == REGISTER_PAYLOAD["email"]
    assert response.json()["roles"] == ["Author"]


async def test_blank_avatar_url_clears_it(client) -> None:
    headers = await sign_in(client)

    response = await client.put(
        "/api/v1/auth/profile",
        json={**VALID_UPDATE, "avatarUrl": "   "},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["avatarUrl"] is None


async def test_invalid_update_reports_field_validation(client) -> None:
    headers = await sign_in(client)

    response = await client.put(
        "/api/v1/auth/profile",
        json={"fullName": "   ", "userName": "no spaces", "avatarUrl": "javascript:alert(1)"},
        headers=headers,
    )

    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/problem+json")
    body = response.json()
    assert body["type"] == "VALIDATION_ERROR"
    assert {"fullName", "userName", "avatarUrl"} <= body["errors"].keys()


async def test_update_rejects_a_user_name_another_account_owns(client) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={
            "fullName": "Tran Nguyen Tuan Anh",
            "email": "tuananh@example.com",
            "userName": "tuananh",
            "password": "StrongPass1!",
        },
    )
    headers = await sign_in(client)

    response = await client.put(
        "/api/v1/auth/profile",
        json={**VALID_UPDATE, "userName": "tuananh"},
        headers=headers,
    )

    assert response.status_code == 409
    assert response.json()["type"] == "USER_NAME_TAKEN"


async def test_update_allows_keeping_the_same_user_name(client) -> None:
    headers = await sign_in(client)

    response = await client.put(
        "/api/v1/auth/profile",
        json={**VALID_UPDATE, "userName": REGISTER_PAYLOAD["userName"]},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["userName"] == REGISTER_PAYLOAD["userName"]
