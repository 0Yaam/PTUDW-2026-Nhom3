"""Admin user directory is paged, searchable, and secret-free."""

from test_recipe_list import create_user


async def test_admin_users_requires_admin_and_filters_without_secrets(client) -> None:
    _, author_headers = await create_user(client, email="directory-author@example.com")
    _, admin_headers = await create_user(client, email="directory-admin@example.com", role="Admin")
    await create_user(client, email="another-author@example.com")

    url = "/api/v1/admin/users?page=1&pageSize=1&role=Author&q=directory"
    assert (await client.get(url)).status_code == 401
    assert (await client.get(url, headers=author_headers)).status_code == 403

    response = await client.get(url, headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["totalCount"] == 1
    assert len(body["items"]) == 1
    assert body["items"][0]["email"] == "directory-author@example.com"
    assert "passwordHash" not in body["items"][0]
    assert "token" not in body["items"][0]


async def test_admin_users_openapi_documents_pagination(client) -> None:
    document = (await client.get("/openapi.json")).json()
    operation = document["paths"]["/api/v1/admin/users"]["get"]
    assert {"401", "403", "200"}.issubset(operation["responses"])
    assert "AdminUserPage" in str(operation["responses"]["200"])
