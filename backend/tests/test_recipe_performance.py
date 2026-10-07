"""Issue #47: durable image resizing, shared cache, and bounded read queries."""

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
from culinary_blog_api.recipes.image_worker import process_due_job, render_variants
from culinary_blog_api.recipes.model import RecipeImage, RecipeImageResizeJob
from culinary_blog_api.recipes.router import get_recipe_storage
from culinary_blog_api.storage import StoredFile
from culinary_blog_api.storage.service import MAX_IMAGE_BYTES, validate_image


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
        assert storage.files == {}
    finally:
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
        assert storage.files == {}
        assert not await process_due_job(storage=storage)
        async with SessionFactory() as session:
            assert await session.scalar(select(RecipeImageResizeJob)) is None
    finally:
        app.dependency_overrides.pop(get_recipe_storage, None)


async def test_read_queries_have_bounded_statement_count(client) -> None:
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
            ("/api/v1/recipes?pageSize=8", 2),
            ("/api/v1/recipes/search?q=Phở&pageSize=8", 2),
            (f"/api/v1/recipes/{recipes[0].slug}", 5),
        ):
            statements.clear()
            response = await client.get(url)
            assert response.status_code == 200
            assert len(statements) <= upper_bound, (url, statements)
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", record)
