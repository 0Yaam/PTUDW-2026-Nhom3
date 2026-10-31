"""Issue #43: public search, archiving, and owner-controlled images."""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from test_recipe_list import add_recipe, create_category, create_user

from culinary_blog_api.db import SessionFactory
from culinary_blog_api.main import app
from culinary_blog_api.recipes.model import (
    Recipe,
    RecipeImage,
    RecipeImageResizeJob,
    RecipeStatus,
)
from culinary_blog_api.recipes.router import get_recipe_storage
from culinary_blog_api.storage import StorageUnavailable
from culinary_blog_api.storage.model import FileDeletionJob
from culinary_blog_api.storage.service import MAX_IMAGE_BYTES, validate_image
from culinary_blog_api.storage.worker import process_due_job as process_cleanup_job

PNG = b"\x89PNG\r\n\x1a\n" + b"image"


class FakeStorage:
    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}
        self.unavailable = False

    async def upload_file(self, file, folder: str) -> str:
        if self.unavailable:
            raise StorageUnavailable("offline")
        data = await file.read(MAX_IMAGE_BYTES + 1)
        validate_image(data, file.content_type or "")
        url = f"http://storage.test/{folder}/{uuid.uuid4().hex}.png"
        self.files[url] = data
        return url

    async def delete(self, url: str) -> None:
        if self.unavailable:
            raise StorageUnavailable("offline")
        self.files.pop(url, None)

    async def delete_variant(self, recipe_id, image_id, size: str) -> None:
        self.files.pop(f"http://storage.test/recipes/{recipe_id}/{image_id}/{size}.webp", None)


async def test_search_is_public_and_combines_filters_sort_and_pagination(client) -> None:
    category = await create_category()
    other = await create_category("Other")
    author, headers = await create_user(client, email="search-author@example.com")
    first = await add_recipe(category, author, title="Phở gà", cook_time=15)
    second = await add_recipe(category, author, title="Phở bò", cook_time=20)
    await add_recipe(category, author, title="Phở nháp", status=RecipeStatus.DRAFT)
    await add_recipe(category, author, title="Phở lưu trữ", status=RecipeStatus.ARCHIVED)
    await add_recipe(category, author, title="Phở đã xoá", is_deleted=True)
    await add_recipe(other, author, title="Phở nơi khác")

    params = {
        "q": "Phở",
        "categoryId": str(category.id),
        "difficulty": "Easy",
        "maxCookTime": 20,
        "minServings": 4,
        "sort": "title",
        "pageSize": 1,
    }
    page1 = await client.get("/api/v1/recipes/search", params=params)
    page2 = await client.get(
        "/api/v1/recipes/search", params={**params, "page": 2}, headers=headers
    )

    assert page1.status_code == 200
    assert page1.json()["totalCount"] == 2
    assert page1.json()["totalPages"] == 2
    assert page1.json()["items"][0]["id"] == str(second.id)
    assert "relevanceScore" in page1.json()["items"][0]
    assert page2.status_code == 200
    assert page2.json()["items"][0]["id"] == str(first.id)


async def test_search_invalid_and_empty_result(client) -> None:
    invalid = await client.get("/api/v1/recipes/search?q=%20%20")
    assert invalid.status_code == 422
    assert invalid.headers["content-type"].startswith("application/problem+json")
    assert invalid.json()["errors"]["q"]
    for query_string in ("q=x", "q=pho&page=0", "q=pho&sort=unknown"):
        response = await client.get(f"/api/v1/recipes/search?{query_string}")
        assert response.status_code == 422
        assert response.headers["content-type"].startswith("application/problem+json")
    empty = await client.get("/api/v1/recipes/search?q=absent")
    assert empty.status_code == 200
    assert empty.json()["items"] == []
    invalid_token = await client.get(
        "/api/v1/recipes/search?q=pho", headers={"Authorization": "Bearer bad"}
    )
    assert invalid_token.status_code == 401


async def test_archive_requires_owner_and_removes_public_recipe(client) -> None:
    category = await create_category()
    owner, owner_headers = await create_user(client, email="archive-owner@example.com")
    _, other_headers = await create_user(client, email="archive-other@example.com")
    _, admin_headers = await create_user(client, email="archive-admin@example.com", role="Admin")
    recipe = await add_recipe(category, owner, title="Lưu trữ món")
    path = f"/api/v1/recipes/{recipe.id}/archive"

    assert (await client.get("/api/v1/recipes")).json()["totalCount"] == 1
    assert (await client.patch(path)).status_code == 401
    assert (await client.patch(path, headers=other_headers)).status_code == 403
    response = await client.patch(path, headers=owner_headers)
    assert response.status_code == 200
    assert response.json()["status"] == "Archived"
    assert (await client.get("/api/v1/recipes")).json()["items"] == []
    assert (await client.get("/api/v1/recipes/search?q=Lưu")).json()["items"] == []
    assert (await client.patch(path, headers=admin_headers)).status_code == 200
    assert (
        await client.patch(f"/api/v1/recipes/{uuid.uuid4()}/archive", headers=owner_headers)
    ).status_code == 404
    async with SessionFactory() as session:
        assert (await session.get(Recipe, recipe.id)).status == RecipeStatus.ARCHIVED


async def test_images_persist_primary_switch_and_delete(client) -> None:
    storage = FakeStorage()
    app.dependency_overrides[get_recipe_storage] = lambda: storage
    try:
        category = await create_category()
        owner, headers = await create_user(client, email="image-owner@example.com")
        recipe = await add_recipe(category, owner, title="Ảnh món ăn")
        path = f"/api/v1/recipes/{recipe.id}/images"
        first = await client.post(
            path, headers=headers, files={"file": ("a.png", PNG, "image/png")}
        )
        second = await client.post(
            path, headers=headers, files={"file": ("b.png", PNG, "image/png")}
        )
        assert first.status_code == second.status_code == 201
        assert first.json()["isPrimary"] is True
        assert second.json()["isPrimary"] is False
        assert len(storage.files) == 2
        image_path = f"{path}/{second.json()['id']}"
        _, other_headers = await create_user(client, email="image-switch-other@example.com")
        assert (await client.patch(image_path, json={"isPrimary": True})).status_code == 401
        assert (
            await client.patch(image_path, headers=other_headers, json={"isPrimary": True})
        ).status_code == 403
        assert (await client.delete(image_path, headers=other_headers)).status_code == 403
        assert (
            await client.patch(image_path, headers=headers, json={"isPrimary": False})
        ).status_code == 422
        assert (
            await client.patch(f"{path}/{uuid.uuid4()}", headers=headers, json={"isPrimary": True})
        ).status_code == 404
        changed = await client.patch(image_path, headers=headers, json={"isPrimary": True})
        assert changed.status_code == 200
        assert changed.json()["isPrimary"] is True
        assert (await client.patch(f"{image_path}/primary", headers=headers)).status_code == 200
        async with SessionFactory() as session:
            rows = list(
                await session.scalars(select(RecipeImage).where(RecipeImage.recipe_id == recipe.id))
            )
            assert len(rows) == 2
            assert [row.id for row in rows if row.is_primary] == [uuid.UUID(second.json()["id"])]
        deleted = await client.delete(image_path, headers=headers)
        assert deleted.status_code == 204
        assert len(storage.files) == 2  # cleanup happens after the metadata transaction
        while await process_cleanup_job(storage=storage):
            pass
        assert len(storage.files) == 1
        async with SessionFactory() as session:
            row = await session.get(RecipeImage, uuid.UUID(first.json()["id"]))
            assert row is not None and row.is_primary
    finally:
        app.dependency_overrides.pop(get_recipe_storage, None)


async def test_images_reject_invalid_file_permission_and_storage_failure(client) -> None:
    storage = FakeStorage()
    app.dependency_overrides[get_recipe_storage] = lambda: storage
    try:
        category = await create_category()
        owner, headers = await create_user(client, email="image-errors-owner@example.com")
        _, other_headers = await create_user(client, email="image-errors-other@example.com")
        recipe = await add_recipe(category, owner, title="Kiểm tra ảnh")
        path = f"/api/v1/recipes/{recipe.id}/images"
        files = {"file": ("a.png", PNG, "image/png")}
        assert (await client.post(path, files=files)).status_code == 401
        assert (await client.post(path, headers=other_headers, files=files)).status_code == 403
        bad = await client.post(
            path, headers=headers, files={"file": ("a.png", b"bad", "image/png")}
        )
        assert bad.status_code == 400
        assert bad.headers["content-type"].startswith("application/problem+json")
        huge = await client.post(
            path,
            headers=headers,
            files={"file": ("a.png", PNG + b"x" * MAX_IMAGE_BYTES, "image/png")},
        )
        assert huge.status_code == 400
        storage.unavailable = True
        unavailable = await client.post(path, headers=headers, files=files)
        assert unavailable.status_code == 503
        assert unavailable.json()["type"] == "IMAGE_STORAGE_UNAVAILABLE"
        assert storage.files == {}
    finally:
        app.dependency_overrides.pop(get_recipe_storage, None)


async def test_replace_image_keeps_position_and_primary_without_leaking_old_objects(client) -> None:
    storage = FakeStorage()
    app.dependency_overrides[get_recipe_storage] = lambda: storage
    try:
        category = await create_category()
        owner, headers = await create_user(client, email="image-replace-owner@example.com")
        recipe = await add_recipe(category, owner, title="Thay ảnh món ăn")
        path = f"/api/v1/recipes/{recipe.id}/images"
        first = await client.post(
            path, headers=headers, files={"file": ("a.png", PNG, "image/png")}
        )
        second = await client.post(
            path, headers=headers, files={"file": ("b.png", PNG, "image/png")}
        )
        assert first.status_code == second.status_code == 201
        old_image = first.json()
        old_medium = f"http://storage.test/recipes/{recipe.id}/{old_image['id']}/medium.webp"
        old_thumbnail = f"http://storage.test/recipes/{recipe.id}/{old_image['id']}/thumbnail.webp"
        storage.files[old_medium] = b"old medium"
        storage.files[old_thumbnail] = b"old thumbnail"

        replacement = await client.post(
            f"{path}/{old_image['id']}/replace",
            headers=headers,
            files={"file": ("new.png", PNG + b"new", "image/png")},
        )
        assert replacement.status_code == 201
        body = replacement.json()
        assert body["id"] != old_image["id"]
        assert body["isPrimary"] is True
        assert body["orderIndex"] == old_image["orderIndex"]
        assert body["mediumUrl"] is None and body["thumbnailUrl"] is None
        assert replacement.headers["location"] == f"{path}/{body['id']}"
        detail = await client.get(f"/api/v1/recipes/{recipe.slug}")
        assert [image["id"] for image in detail.json()["images"]] == [
            body["id"], second.json()["id"]
        ]
        async with SessionFactory() as session:
            assert await session.get(RecipeImage, uuid.UUID(old_image["id"])) is None
            jobs = list(await session.scalars(select(RecipeImageResizeJob)))
            assert all(job.image_id != uuid.UUID(old_image["id"]) for job in jobs)
            assert any(job.image_id == uuid.UUID(body["id"]) for job in jobs)
            cleanup = list(await session.scalars(select(FileDeletionJob)))
            assert len(cleanup) == 3

        new_medium = f"http://storage.test/recipes/{recipe.id}/{body['id']}/medium.webp"
        new_thumbnail = f"http://storage.test/recipes/{recipe.id}/{body['id']}/thumbnail.webp"
        storage.files[new_medium] = b"new medium"
        storage.files[new_thumbnail] = b"new thumbnail"
        while await process_cleanup_job(storage=storage):
            pass
        assert old_image["originalUrl"] not in storage.files
        assert old_medium not in storage.files and old_thumbnail not in storage.files
        assert body["originalUrl"] in storage.files
        assert new_medium in storage.files and new_thumbnail in storage.files

        second_replacement = await client.post(
            f"{path}/{second.json()['id']}/replace",
            headers=headers,
            files={"file": ("new-second.png", PNG + b"second", "image/png")},
        )
        assert second_replacement.status_code == 201
        assert second_replacement.json()["isPrimary"] is False
        assert second_replacement.json()["orderIndex"] == 1
        refreshed = await client.get(f"/api/v1/recipes/{recipe.slug}")
        assert [image["id"] for image in refreshed.json()["images"]] == [
            body["id"], second_replacement.json()["id"]
        ]
        assert [image["id"] for image in refreshed.json()["images"] if image["isPrimary"]] == [
            body["id"]
        ]
    finally:
        app.dependency_overrides.pop(get_recipe_storage, None)


async def test_replace_image_rejects_other_users_invalid_files_and_missing_image(client) -> None:
    storage = FakeStorage()
    app.dependency_overrides[get_recipe_storage] = lambda: storage
    try:
        category = await create_category()
        owner, headers = await create_user(client, email="replace-owner@example.com")
        _, other_headers = await create_user(client, email="replace-other@example.com")
        recipe = await add_recipe(category, owner, title="Thay ảnh được bảo vệ")
        path = f"/api/v1/recipes/{recipe.id}/images"
        uploaded = await client.post(
            path, headers=headers, files={"file": ("a.png", PNG, "image/png")}
        )
        image_path = f"{path}/{uploaded.json()['id']}/replace"
        files = {"file": ("b.png", PNG, "image/png")}
        assert (await client.post(image_path, files=files)).status_code == 401
        assert (
            await client.post(image_path, headers=other_headers, files=files)
        ).status_code == 403
        assert (
            await client.post(
                f"{path}/{uuid.uuid4()}/replace", headers=headers, files=files
            )
        ).status_code == 404
        invalid = await client.post(
            image_path,
            headers=headers,
            files={"file": ("bad.png", b"bad", "image/png")},
        )
        assert invalid.status_code == 400
        assert invalid.headers["content-type"].startswith("application/problem+json")
        storage.unavailable = True
        assert (
            await client.post(image_path, headers=headers, files=files)
        ).status_code == 503
        async with SessionFactory() as session:
            assert await session.get(RecipeImage, uuid.UUID(uploaded.json()["id"])) is not None
        assert len(storage.files) == 1
    finally:
        app.dependency_overrides.pop(get_recipe_storage, None)


async def test_admin_delete_queues_retryable_cleanup(client) -> None:
    storage = FakeStorage()
    app.dependency_overrides[get_recipe_storage] = lambda: storage
    try:
        category = await create_category()
        owner, _ = await create_user(client, email="image-admin-owner@example.com")
        _, admin_headers = await create_user(
            client, email="image-admin@example.com", role="Admin"
        )
        recipe = await add_recipe(category, owner, title="Ảnh do admin quản lý")
        path = f"/api/v1/recipes/{recipe.id}/images"
        upload = await client.post(
            path, headers=admin_headers, files={"file": ("a.png", PNG, "image/png")}
        )
        assert upload.status_code == 201
        image_id = uuid.UUID(upload.json()["id"])
        storage.unavailable = True
        deleted = await client.delete(f"{path}/{image_id}", headers=admin_headers)
        assert deleted.status_code == 204
        async with SessionFactory() as session:
            assert await session.get(RecipeImage, image_id) is None
            jobs = list(await session.scalars(select(FileDeletionJob)))
            assert len(jobs) == 3
        assert await process_cleanup_job(storage=storage)
        storage.unavailable = False
        later = datetime.now(UTC) + timedelta(hours=1)
        while await process_cleanup_job(storage=storage, now=later):
            pass
        assert storage.files == {}
        async with SessionFactory() as session:
            jobs = await session.scalars(select(FileDeletionJob))
            assert all(job.status == "Done" for job in jobs)
    finally:
        app.dependency_overrides.pop(get_recipe_storage, None)


async def test_recipe_delete_queues_all_image_objects(client) -> None:
    storage = FakeStorage()
    app.dependency_overrides[get_recipe_storage] = lambda: storage
    try:
        category = await create_category()
        owner, headers = await create_user(client, email="recipe-cleanup@example.com")
        recipe = await add_recipe(category, owner, title="Recipe with file cleanup")
        upload = await client.post(
            f"/api/v1/recipes/{recipe.id}/images",
            headers=headers,
            files={"file": ("a.png", PNG, "image/png")},
        )
        assert upload.status_code == 201
        deleted = await client.delete(f"/api/v1/recipes/{recipe.id}", headers=headers)
        assert deleted.status_code == 204
        async with SessionFactory() as session:
            assert await session.get(Recipe, recipe.id) is None
            jobs = list(await session.scalars(select(FileDeletionJob)))
            assert len(jobs) == 3
        while await process_cleanup_job(storage=storage):
            pass
        assert storage.files == {}
    finally:
        app.dependency_overrides.pop(get_recipe_storage, None)
