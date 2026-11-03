"""Admin users endpoint provides role-restricted, paginated user management."""

from test_recipe_list import create_user


async def test_admin_users_requires_admin(client) -> None:
    _, author_headers = await create_user(client, email="author-user-test@example.com")
    _, admin_headers = await create_user(
        client, email="admin-user-test@example.com", role="Admin"
    )

    url = "/api/v1/admin/users"
    anonymous = await client.get(url)
    assert anonymous.status_code == 401
    assert anonymous.headers["content-type"].startswith("application/problem+json")

    author_res = await client.get(url, headers=author_headers)
    assert author_res.status_code == 403
    assert author_res.headers["content-type"].startswith("application/problem+json")

    admin_res = await client.get(url, headers=admin_headers)
    assert admin_res.status_code == 200
    data = admin_res.json()
    assert "items" in data
    assert "totalCount" in data
    assert data["totalCount"] >= 2


async def test_admin_users_pagination_and_sorting(client) -> None:
    _, admin_headers = await create_user(
        client, email="admin-page-test@example.com", role="Admin"
    )
    for i in range(3):
        await create_user(client, email=f"author-paged-{i}@example.com")

    res = await client.get("/api/v1/admin/users?page=1&pageSize=2", headers=admin_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["page"] == 1
    assert data["pageSize"] == 2
    assert len(data["items"]) == 2
    assert data["hasNextPage"] is True
    assert data["hasPreviousPage"] is False

    res_page2 = await client.get(
        "/api/v1/admin/users?page=2&pageSize=2", headers=admin_headers
    )
    assert res_page2.status_code == 200
    data2 = res_page2.json()
    assert data2["page"] == 2
    assert data2["hasPreviousPage"] is True


async def test_admin_users_search_and_role_filter(client) -> None:
    _, admin_headers = await create_user(
        client, email="admin-search-unique@example.com", role="Admin"
    )
    author, _ = await create_user(
        client, email="author-search-special@example.com", role="Author"
    )

    # Search by email
    search_res = await client.get(
        "/api/v1/admin/users?q=author-search-special", headers=admin_headers
    )
    assert search_res.status_code == 200
    items = search_res.json()["items"]
    assert any(u["email"] == author.email for u in items)

    # Filter by role Author
    author_res = await client.get("/api/v1/admin/users?role=Author", headers=admin_headers)
    assert author_res.status_code == 200
    assert all(u["role"] == "Author" for u in author_res.json()["items"])

    # Filter by role Admin
    admin_only_res = await client.get(
        "/api/v1/admin/users?role=Admin", headers=admin_headers
    )
    assert admin_only_res.status_code == 200
    assert all(u["role"] == "Admin" for u in admin_only_res.json()["items"])


async def test_admin_users_does_not_leak_sensitive_fields(client) -> None:
    _, admin_headers = await create_user(
        client, email="admin-leak-test@example.com", role="Admin"
    )

    res = await client.get("/api/v1/admin/users", headers=admin_headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data["items"]) > 0

    sensitive_keys = {
        "password",
        "passwordHash",
        "password_hash",
        "tokens",
        "sessionVersion",
        "session_version",
        "accessFailedCount",
        "access_failed_count",
        "lockoutUntil",
        "lockout_until",
    }
    for item in data["items"]:
        keys = set(item.keys())
        assert not (keys & sensitive_keys), f"Exposed sensitive key: {keys & sensitive_keys}"
        assert "id" in item
        assert "fullName" in item
        assert "email" in item
        assert "userName" in item
        assert "role" in item
        assert "createdAt" in item


async def test_admin_users_openapi_contract(client) -> None:
    openapi = (await client.get("/openapi.json")).json()
    endpoint = openapi["paths"]["/api/v1/admin/users"]["get"]
    assert "200" in endpoint["responses"]
    assert "401" in endpoint["responses"]
    assert "403" in endpoint["responses"]
