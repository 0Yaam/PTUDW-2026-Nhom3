"""Issues #47/#61: resize recovery, cache consistency, and bounded read queries."""

import asyncio
import importlib
import uuid
from datetime import UTC, datetime, timedelta
from io import BytesIO

from PIL import Image
from redis.exceptions import RedisError
from sqlalchemy import event, select
from test_recipe_list import add_recipe, create_category, create_user

from culinary_blog_api.db import SessionFactory, engine
from culinary_blog_api.main import app
from culinary_blog_api.recipes import Ingredient, RecipeIngredient, RecipeStep, cache
from culinary_blog_api.recipes.image_worker import (
    LEASE,
    _claim,
    _process,
    _schedule_failure,
    process_due_job,
    render_variants,
)
from culinary_blog_api.recipes.model import RecipeImage, RecipeImageResizeJob
from culinary_blog_api.recipes.router import get_recipe_storage
from culinary_blog_api.storage import StoredFile
from culinary_blog_api.storage.service import MAX_IMAGE_BYTES, validate_image
from culinary_blog_api.storage.worker import process_due_job as process_cleanup_job


class MemoryRedis:
    def __init__(self) -> None:
        self.values: dict[str, bytes] = {}
        self.ttls: dict[str, int] = {}
        self.offline = False

    async def get(self, key: str) -> bytes | None:
        if self.offline:
            raise RedisError("offline")
        return self.values.get(key)

    async def set(self, key: str, value: str, *, ex: int) -> None:
        if self.offline:
            raise RedisError("offline")
        self.values[key] = value.encode()
        self.ttls[key] = ex

    async def incr(self, key: str) -> int:
        if self.offline:
            raise RedisError("offline")
        version = int(self.values.get(key, b"0")) + 1
        self.values[key] = str(version).encode()
        return version


def png_image() -> bytes:
    output = BytesIO()
    Image.new("RGBA", (1200, 900), (220, 80, 40, 140)).save(output, format="PNG")
    return output.getvalue()


class MemoryStorage:
    def __init__(self) -> None:
        self.files: dict[str, StoredFile] = {}
        self.fail_variant = False

    async def upload_file(self, file, folder: str) -> str:
        data = await file.read(MAX_IMAGE_BYTES + 1)
        validate_image(data, file.content_type or "")
        url = f"http://storage.test/{folder}/{uuid.uuid4().hex}.png"
        self.files[url] = StoredFile(data, "image/png")
        return url

    async def read(self, file_url: str) -> StoredFile:
        return self.files[file_url]

    def variant_url(self, recipe_id, image_id, size: str) -> str:
        return f"http://storage.test/recipes/{recipe_id}/{image_id}/{size}.webp"

    async def upload_variant(self, data: bytes, recipe_id, image_id, size: str) -> str:
        if self.fail_variant and size == "thumbnail":
            raise OSError("storage offline")
        validate_image(data, "image/webp")
        url = self.variant_url(recipe_id, image_id, size)
        self.files[url] = StoredFile(data, "image/webp")
        return url

    async def delete_variant(self, recipe_id, image_id, size: str) -> None:
        self.files.pop(self.variant_url(recipe_id, image_id, size), None)

    async def delete(self, url: str) -> None:
        self.files.pop(url, None)


def test_resize_accepts_all_upload_formats_and_preserves_alpha() -> None:
    source = Image.new("RGBA", (120, 90), (20, 30, 40, 128))
    for file_format in ("JPEG", "PNG", "WEBP", "AVIF"):
        output = BytesIO()
        prepared = source.convert("RGB") if file_format == "JPEG" else source
        prepared.save(output, format=file_format)
        variants = render_variants(output.getvalue())
        assert set(variants) == {"medium", "thumbnail"}
        with Image.open(BytesIO(variants["thumbnail"])) as thumbnail:
            assert thumbnail.size == (300, 300)
            assert (thumbnail.mode == "RGBA") == (file_format != "JPEG")


async def upload_image(client, storage: MemoryStorage):
    app.dependency_overrides[get_recipe_storage] = lambda: storage
    category = await create_category()
    author, headers = await create_user(client, email=f"image-{uuid.uuid4().hex}@example.com")
    recipe = await add_recipe(category, author, title=f"Ảnh {uuid.uuid4().hex}")
    response = await client.post(
        f"/api/v1/recipes/{recipe.id}/images", headers=headers,
        files={"file": ("recipe.png", png_image(), "image/png")},
    )
    assert response.status_code == 201
    return recipe, headers, response.json()


async def test_redis_cache_hit_ttls_and_mutation_invalidation(client, monkeypatch) -> None:
    redis = MemoryRedis()
    monkeypatch.setattr(cache, "get_cache_client", lambda: redis)
    category = await create_category()
    author, headers = await create_user(client, email="redis-owner@example.com")
    recipe = await add_recipe(category, author, title="Phở Redis")
    urls = (
        "/api/v1/recipes?sort=title",
        f"/api/v1/recipes/{recipe.slug}",
        "/api/v1/recipes/search?q=Phở",
    )
    for url in urls:
        first = await client.get(url)
        second = await client.get(url)
        assert first.status_code == second.status_code == 200
        assert first.headers["X-Recipe-Cache"] == "MISS"
        assert second.headers["X-Recipe-Cache"] == "HIT"
    assert sorted(redis.ttls.values()) == [60, 300, 900]
    archived = await client.patch(f"/api/v1/recipes/{recipe.id}/archive", headers=headers)
    assert archived.status_code == 200
    for url in urls:
        fresh = await client.get(url)
        if url.endswith(recipe.slug):
            assert fresh.status_code == 403
        else:
            assert fresh.headers["X-Recipe-Cache"] == "MISS"
            assert fresh.json()["items"] == []


async def test_expired_search_cache_coalesces_concurrent_database_reads(
    client, monkeypatch
) -> None:
    redis = MemoryRedis()
    monkeypatch.setattr(cache, "get_cache_client", lambda: redis)
    category = await create_category()
    author, _ = await create_user(client, email="search-stampede@example.com")
    await add_recipe(category, author, title="Phở cho nhiều người")
    url = "/api/v1/recipes/search?q=Phở"
    assert (await client.get(url)).headers["X-Recipe-Cache"] == "MISS"
    for key in tuple(redis.values):
        if ":search:" in key:
            redis.values.pop(key)

    recipe_router = importlib.import_module("culinary_blog_api.recipes.router")
    original_search = recipe_router.search_recipes
    loads = 0

    async def counted_search(*args, **kwargs):
        nonlocal loads
        loads += 1
        await asyncio.sleep(0.02)
        return await original_search(*args, **kwargs)

    monkeypatch.setattr(recipe_router, "search_recipes", counted_search)
    responses = await asyncio.gather(*(client.get(url) for _ in range(30)))
    assert all(response.status_code == 200 for response in responses)
    assert all(response.json()["totalCount"] == 1 for response in responses)
    assert loads == 1
    assert sum(response.headers["X-Recipe-Cache"] == "HIT" for response in responses) == 29


async def test_redis_outage_falls_back_to_database(client, monkeypatch) -> None:
    redis = MemoryRedis()
    monkeypatch.setattr(cache, "get_cache_client", lambda: redis)
    category = await create_category()
    author, _ = await create_user(client, email="redis-offline@example.com")
    await add_recipe(category, author, title="Phở vẫn đọc được")
    redis.offline = True
    for url in ("/api/v1/recipes", "/api/v1/recipes/search?q=Phở"):
        response = await client.get(url)
        assert response.status_code == 200
        assert response.headers["X-Recipe-Cache"] == "BYPASS"
        assert response.json()["totalCount"] == 1


async def test_recovered_redis_flushes_failed_invalidation_before_serving_cache(
    client, monkeypatch
) -> None:
    redis = MemoryRedis()
    monkeypatch.setattr(cache, "get_cache_client", lambda: redis)
    category = await create_category()
    author, headers = await create_user(client, email="redis-recover@example.com")
    recipe = await add_recipe(category, author, title="Món cần làm mới")
    url = "/api/v1/recipes?sort=title"
    assert (await client.get(url)).json()["totalCount"] == 1
    assert (await client.get(url)).headers["X-Recipe-Cache"] == "HIT"
    redis.offline = True
    archived = await client.patch(f"/api/v1/recipes/{recipe.id}/archive", headers=headers)
    assert archived.status_code == 200
    assert (await client.get(url)).headers["X-Recipe-Cache"] == "BYPASS"
    redis.offline = False
    fresh = await client.get(url)
    assert fresh.headers["X-Recipe-Cache"] == "MISS"
    assert fresh.json()["items"] == []


async def test_redis_recovery_on_another_api_process_does_not_serve_stale_data(
    client, monkeypatch
) -> None:
    redis = MemoryRedis()
    monkeypatch.setattr(cache, "get_cache_client", lambda: redis)
    category = await create_category()
    author, headers = await create_user(client, email="redis-cross-process@example.com")
    recipe = await add_recipe(category, author, title="Món nhiều tiến trình")
    url = "/api/v1/recipes?sort=title"
    assert (await client.get(url)).headers["X-Recipe-Cache"] == "MISS"
    assert (await client.get(url)).headers["X-Recipe-Cache"] == "HIT"

    redis.offline = True
    assert (
        await client.patch(f"/api/v1/recipes/{recipe.id}/archive", headers=headers)
    ).status_code == 200
    redis.offline = False
    # A second API process has no knowledge of the first process's pending counter.
    monkeypatch.setattr(cache, "_pending_invalidations", 0)
    fresh = await client.get(url)
    assert fresh.headers["X-Recipe-Cache"] == "MISS"
    assert fresh.json()["items"] == []


async def test_ingredient_writes_invalidate_published_recipe_detail(client, monkeypatch) -> None:
    redis = MemoryRedis()
    monkeypatch.setattr(cache, "get_cache_client", lambda: redis)
    category = await create_category()
    author, headers = await create_user(client, email="ingredient-cache@example.com")
    recipe = await add_recipe(category, author, title="Món đổi nguyên liệu")
    detail_url = f"/api/v1/recipes/{recipe.slug}"
    ingredient_url = f"/api/v1/recipes/{recipe.id}/ingredients"

    assert (await client.get(detail_url)).headers["X-Recipe-Cache"] == "MISS"
    assert (await client.get(detail_url)).headers["X-Recipe-Cache"] == "HIT"
    created = await client.post(
        ingredient_url, headers=headers,
        json={"ingredientName": "Muối", "quantity": 1, "unit": "g"},
    )
    assert created.status_code == 201
    after_create = await client.get(detail_url)
    assert after_create.headers["X-Recipe-Cache"] == "MISS"
    assert after_create.json()["ingredients"][0]["quantity"] == 1

    row_url = f"{ingredient_url}/{created.json()['id']}"
    updated = await client.put(
        row_url, headers=headers,
        json={"ingredientName": "Muối", "quantity": 2, "unit": "g"},
    )
    assert updated.status_code == 200
    after_update = await client.get(detail_url)
    assert after_update.headers["X-Recipe-Cache"] == "MISS"
    assert after_update.json()["ingredients"][0]["quantity"] == 2

    assert (await client.delete(row_url, headers=headers)).status_code == 204
    after_delete = await client.get(detail_url)
    assert after_delete.headers["X-Recipe-Cache"] == "MISS"
    assert after_delete.json()["ingredients"] == []


async def test_recipe_step_publication_update_and_delete_invalidate_public_reads(
    client, monkeypatch
) -> None:
    redis = MemoryRedis()
    monkeypatch.setattr(cache, "get_cache_client", lambda: redis)
    category = await create_category()
    author, headers = await create_user(client, email="write-cache@example.com")
    recipe = await add_recipe(category, author, title="Phở cache")
    list_url = "/api/v1/recipes?sort=title"
    detail_url = f"/api/v1/recipes/{recipe.slug}"
    search_url = "/api/v1/recipes/search?q=Phở"
    for url in (list_url, detail_url, search_url):
        assert (await client.get(url)).headers["X-Recipe-Cache"] == "MISS"
        assert (await client.get(url)).headers["X-Recipe-Cache"] == "HIT"

    step_url = f"/api/v1/recipes/{recipe.id}/steps"
    step = await client.post(step_url, headers=headers, json={"instruction": "Nấu nước dùng."})
    assert step.status_code == 201
    assert (await client.get(detail_url)).json()["steps"][0]["instruction"] == "Nấu nước dùng."
    changed_step = await client.put(
        f"{step_url}/{step.json()['id']}", headers=headers,
        json={"instruction": "Ninh nước dùng."},
    )
    assert changed_step.status_code == 200
    changed_detail = await client.get(detail_url)
    assert changed_detail.headers["X-Recipe-Cache"] == "MISS"
    assert changed_detail.json()["steps"][0]["instruction"] == "Ninh nước dùng."

    assert (
        await client.delete(f"{step_url}/{step.json()['id']}", headers=headers)
    ).status_code == 204
    without_step = await client.get(detail_url)
    assert without_step.headers["X-Recipe-Cache"] == "MISS"
    assert without_step.json()["steps"] == []
    replacement = await client.post(
        step_url, headers=headers, json={"instruction": "Ninh nước dùng."}
    )
    assert replacement.status_code == 201

    async with SessionFactory() as session:
        current = await session.get(type(recipe), recipe.id)
        row_version = current.row_version.hex()
    changed_recipe = await client.put(
        f"/api/v1/recipes/{recipe.id}", headers=headers,
        json={
            "title": "Phở cache", "description": "Công thức đã cập nhật.",
            "instructions": "Ninh nước dùng.", "categoryId": str(category.id),
            "prepTimeMinutes": 10, "cookTimeMinutes": 30, "servings": 4,
            "difficulty": 1, "rowVersion": row_version,
        },
    )
    assert changed_recipe.status_code == 200
    for url in (list_url, detail_url, search_url):
        fresh = await client.get(url)
        assert fresh.headers["X-Recipe-Cache"] == "MISS"
    assert (await client.get(detail_url)).json()["description"] == "Công thức đã cập nhật."

    ingredient = await client.post(
        f"/api/v1/recipes/{recipe.id}/ingredients", headers=headers,
        json={"ingredientName": "Bánh phở", "quantity": 1, "unit": "g"},
    )
    assert ingredient.status_code == 201
    unpublished = await client.patch(f"/api/v1/recipes/{recipe.id}/unpublish", headers=headers)
    assert unpublished.status_code == 200
    assert (await client.get(list_url)).json()["items"] == []
    assert (await client.get(search_url)).json()["items"] == []
    assert (await client.get(detail_url)).status_code == 403

    published = await client.patch(f"/api/v1/recipes/{recipe.id}/publish", headers=headers)
    assert published.status_code == 200
    assert (await client.get(detail_url)).status_code == 200
    deleted = await client.delete(f"/api/v1/recipes/{recipe.id}", headers=headers)
    assert deleted.status_code == 204
    assert (await client.get(list_url)).json()["items"] == []
    assert (await client.get(detail_url)).status_code == 404


async def test_rolled_back_recipe_write_keeps_cache_generation(client, monkeypatch) -> None:
    redis = MemoryRedis()
    monkeypatch.setattr(cache, "get_cache_client", lambda: redis)
    category = await create_category()
    author, _ = await create_user(client, email="rollback-cache@example.com")
    recipe = await add_recipe(category, author, title="Phở giữ nguyên")
    url = f"/api/v1/recipes/{recipe.slug}"
    assert (await client.get(url)).headers["X-Recipe-Cache"] == "MISS"
    assert (await client.get(url)).headers["X-Recipe-Cache"] == "HIT"
    async with SessionFactory() as session:
        row = await session.get(type(recipe), recipe.id)
        row.description = "Thay đổi chưa commit"
        await session.flush()
        await session.rollback()
    cached = await client.get(url)
    assert cached.headers["X-Recipe-Cache"] == "HIT"
    assert cached.json()["description"] == recipe.description


async def test_concurrent_cache_reads_share_one_generation_query() -> None:
    selects: list[str] = []

    def record(_conn, _cursor, statement, _params, _context, _many) -> None:
        if "FROM recipe_cache_generation" in statement:
            selects.append(statement)

    event.listen(engine.sync_engine, "before_cursor_execute", record)
    try:
        versions = await asyncio.gather(*(cache._committed_generation() for _ in range(40)))
        assert versions == ["0"] * 40
        assert len(selects) == 1
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", record)


async def test_upload_outbox_worker_variants_and_delete(client, monkeypatch) -> None:
    redis = MemoryRedis()
    monkeypatch.setattr(cache, "get_cache_client", lambda: redis)
    storage = MemoryStorage()
    try:
        recipe, headers, payload = await upload_image(client, storage)
        image_id = uuid.UUID(payload["id"])
        assert payload["mediumUrl"] is None and payload["thumbnailUrl"] is None
        async with SessionFactory() as session:
            job = await session.scalar(select(RecipeImageResizeJob))
            assert job.image_id == image_id and job.status == "Pending"
        detail_url = f"/api/v1/recipes/{recipe.slug}"
        assert (await client.get(detail_url)).json()["images"][0]["mediumUrl"] is None
        assert await process_due_job(storage=storage, now=datetime.now(UTC) + timedelta(seconds=1))
        assert not await process_due_job(storage=storage)
        detail = await client.get(detail_url)
        assert detail.headers["X-Recipe-Cache"] == "MISS"
        images = detail.json()["images"]
        assert len(images) == 1
        assert images[0]["mediumUrl"] == storage.variant_url(recipe.id, image_id, "medium")
        assert images[0]["thumbnailUrl"] == storage.variant_url(recipe.id, image_id, "thumbnail")
        for size, dimensions in (("medium", (800, 600)), ("thumbnail", (300, 300))):
            variant = storage.files[storage.variant_url(recipe.id, image_id, size)]
            with Image.open(BytesIO(variant.data)) as rendered:
                assert rendered.size == dimensions
                assert rendered.format == "WEBP"
        deleted = await client.delete(
            f"/api/v1/recipes/{recipe.id}/images/{image_id}", headers=headers
        )
        assert deleted.status_code == 204
        without_image = await client.get(detail_url)
        assert without_image.headers["X-Recipe-Cache"] == "MISS"
        assert without_image.json()["images"] == []
        while await process_cleanup_job(storage=storage):
            pass
        assert storage.files == {}
    finally:
        app.dependency_overrides.pop(get_recipe_storage, None)


async def test_primary_image_update_and_delete_invalidate_detail(client, monkeypatch) -> None:
    redis = MemoryRedis()
    monkeypatch.setattr(cache, "get_cache_client", lambda: redis)
    storage = MemoryStorage()
    try:
        recipe, headers, first = await upload_image(client, storage)
        url = f"/api/v1/recipes/{recipe.slug}"
        assert (await client.get(url)).headers["X-Recipe-Cache"] == "MISS"
        second = await client.post(
            f"/api/v1/recipes/{recipe.id}/images", headers=headers,
            files={"file": ("another.png", png_image(), "image/png")},
        )
        assert second.status_code == 201
        with_two = await client.get(url)
        assert with_two.headers["X-Recipe-Cache"] == "MISS"
        assert len(with_two.json()["images"]) == 2

        second_url = f"/api/v1/recipes/{recipe.id}/images/{second.json()['id']}"
        promoted = await client.patch(
            second_url, headers=headers, json={"isPrimary": True}
        )
        assert promoted.status_code == 200
        after_primary = await client.get(url)
        assert after_primary.headers["X-Recipe-Cache"] == "MISS"
        assert next(image for image in after_primary.json()["images"] if image["isPrimary"])[
            "id"
        ] == second.json()["id"]

        assert (await client.delete(second_url, headers=headers)).status_code == 204
        after_delete = await client.get(url)
        assert after_delete.headers["X-Recipe-Cache"] == "MISS"
        assert [image["id"] for image in after_delete.json()["images"]] == [first["id"]]
        assert after_delete.json()["images"][0]["isPrimary"] is True
    finally:
        app.dependency_overrides.pop(get_recipe_storage, None)


async def test_upload_inserts_image_before_resize_job_foreign_key(client) -> None:
    storage = MemoryStorage()
    inserts: list[str] = []

    def record(_conn, _cursor, statement, _params, _context, _many) -> None:
        if statement.lstrip().upper().startswith("INSERT INTO RECIPE_"):
            inserts.append(statement.lower())

    event.listen(engine.sync_engine, "before_cursor_execute", record)
    try:
        await upload_image(client, storage)
        image_index = next(
            index for index, sql in enumerate(inserts) if "insert into recipe_images" in sql
        )
        job_index = next(
            index for index, sql in enumerate(inserts)
            if "insert into recipe_image_resize_jobs" in sql
        )
        assert image_index < job_index
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", record)
        app.dependency_overrides.pop(get_recipe_storage, None)


async def test_worker_retry_overwrites_same_object_and_eventually_fails(client) -> None:
    storage = MemoryStorage()
    try:
        recipe, _headers, payload = await upload_image(client, storage)
        image_id = uuid.UUID(payload["id"])
        storage.fail_variant = True
        clock = datetime.now(UTC) + timedelta(seconds=1)
        for attempt, seconds in enumerate((60, 300, 1800), 1):
            assert await process_due_job(storage=storage, now=clock)
            async with SessionFactory() as session:
                job = await session.scalar(select(RecipeImageResizeJob))
                assert job.status == "Pending" and job.attempts == attempt
                assert job.next_attempt_at.replace(tzinfo=UTC) == clock + timedelta(seconds=seconds)
            assert len(storage.files) == 2  # Original + one deterministic medium object.
            clock += timedelta(seconds=seconds)
        assert await process_due_job(storage=storage, now=clock)
        async with SessionFactory() as session:
            job = await session.scalar(select(RecipeImageResizeJob))
            image = await session.get(RecipeImage, image_id)
            assert job.status == "Failed" and job.attempts == 4
            assert image.medium_url is None and image.thumbnail_url is None
        assert not await process_due_job(storage=storage, now=clock + timedelta(days=1))
        # A delete also removes a variant uploaded by a failed attempt.
        await storage.delete_variant(recipe.id, image_id, "medium")
        assert len(storage.files) == 1
    finally:
        app.dependency_overrides.pop(get_recipe_storage, None)


async def test_expired_worker_claim_recovers_and_stale_failure_cannot_reset_new_claim(
    client
) -> None:
    storage = MemoryStorage()
    try:
        recipe, _headers, payload = await upload_image(client, storage)
        image_id = uuid.UUID(payload["id"])
        clock = datetime.now(UTC) + timedelta(seconds=1)
        first_claim = await _claim(clock)
        assert first_claim is not None
        second_clock = clock + LEASE + timedelta(seconds=1)
        second_claim = await _claim(second_clock)
        assert second_claim is not None
        assert second_claim.job_id == first_claim.job_id
        assert second_claim.attempt == 2

        assert not await _process(first_claim, storage, second_clock)
        assert len(storage.files) == 1

        await _schedule_failure(first_claim, OSError("old worker failed"), second_clock)
        async with SessionFactory() as session:
            job = await session.scalar(select(RecipeImageResizeJob))
            assert job.status == "Processing" and job.attempts == 2

        assert await process_due_job(storage=storage, now=second_clock + LEASE)
        async with SessionFactory() as session:
            job = await session.scalar(select(RecipeImageResizeJob))
            image = await session.get(RecipeImage, image_id)
            assert job.status == "Done" and job.attempts == 3
            assert image.medium_url and image.thumbnail_url
        assert len(storage.files) == 3
    finally:
        app.dependency_overrides.pop(get_recipe_storage, None)


async def test_delete_before_worker_cancels_job_and_cleans_partial_variant(client) -> None:
    storage = MemoryStorage()
    try:
        recipe, headers, payload = await upload_image(client, storage)
        image_id = uuid.UUID(payload["id"])
        await storage.upload_variant(b"RIFF1234WEBPdemo", recipe.id, image_id, "medium")
        deleted = await client.delete(
            f"/api/v1/recipes/{recipe.id}/images/{image_id}", headers=headers
        )
        assert deleted.status_code == 204
        while await process_cleanup_job(storage=storage):
            pass
        assert storage.files == {}
        assert not await process_due_job(storage=storage)
        async with SessionFactory() as session:
            assert await session.scalar(select(RecipeImageResizeJob)) is None
    finally:
        app.dependency_overrides.pop(get_recipe_storage, None)


async def test_read_queries_have_bounded_statement_count(client, monkeypatch) -> None:
    redis = MemoryRedis()
    monkeypatch.setattr(cache, "get_cache_client", lambda: redis)
    category = await create_category()
    author, _ = await create_user(client, email="query-count@example.com")
    recipes = [await add_recipe(category, author, title=f"Phở {i}") for i in range(8)]
    async with SessionFactory() as session:
        for recipe in recipes:
            for index in range(5):
                ingredient = Ingredient(name=f"Nguyên liệu {recipe.id} {index}")
                session.add(ingredient)
                await session.flush()
                session.add(RecipeIngredient(
                    recipe_id=recipe.id, ingredient_id=ingredient.id,
                    quantity=1, unit="g", order_index=index,
                ))
                session.add(RecipeStep(
                    recipe_id=recipe.id, step_number=index + 1, instruction="Nấu chín."
                ))
                session.add(RecipeImage(
                    recipe_id=recipe.id, original_url=f"http://storage.test/{uuid.uuid4().hex}",
                    is_primary=index == 0, order_index=index,
                ))
        await session.commit()

    statements: list[str] = []

    def record(_conn, _cursor, statement, _params, _context, _many) -> None:
        if statement.lstrip().upper().startswith("SELECT"):
            statements.append(statement)

    event.listen(engine.sync_engine, "before_cursor_execute", record)
    try:
        for url, upper_bound in (
            ("/api/v1/recipes?pageSize=8", 3),
            ("/api/v1/recipes/search?q=Phở&pageSize=8", 3),
            (f"/api/v1/recipes/{recipes[0].slug}", 6),
        ):
            statements.clear()
            response = await client.get(url)
            assert response.status_code == 200
            assert len(statements) <= upper_bound, (url, statements)
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", record)
