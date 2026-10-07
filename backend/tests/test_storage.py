"""The shared image adapter validates content and confines URLs to its bucket."""

import uuid
from io import BytesIO

import pytest
from botocore.exceptions import ClientError
from pydantic import SecretStr

from culinary_blog_api.config import Settings
from culinary_blog_api.storage import (
    MAX_IMAGE_BYTES,
    InvalidImage,
    S3FileStorage,
    StorageNotFound,
    StorageUnavailable,
)


class FakeS3:
    def __init__(self) -> None:
        self.objects: dict[str, tuple[bytes, str]] = {}
        self.fail = False
        self.transient_failures = 0

    def put_object(self, *, Bucket: str, Key: str, Body: bytes, ContentType: str) -> None:
        if self.fail:
            raise OSError("store offline")
        if self.transient_failures:
            self.transient_failures -= 1
            raise OSError("temporary outage")
        assert Bucket == "culinary-blog"
        self.objects[Key] = (Body, ContentType)

    def get_object(self, *, Bucket: str, Key: str) -> dict:
        if self.fail:
            raise OSError("store offline")
        assert Bucket == "culinary-blog"
        if Key not in self.objects:
            raise ClientError(
                {"Error": {"Code": "NoSuchKey", "Message": "Missing"}}, "GetObject"
            )
        data, content_type = self.objects[Key]
        return {"Body": BytesIO(data), "ContentType": content_type}

    def delete_object(self, *, Bucket: str, Key: str) -> None:
        if self.fail:
            raise OSError("store offline")
        assert Bucket == "culinary-blog"
        self.objects.pop(Key, None)


def storage_settings() -> Settings:
    return Settings(
        _env_file=None,
        minio_endpoint="http://minio:9000",
        minio_public_url="http://localhost:9000",
        minio_access_key="test-access",
        minio_secret_key=SecretStr("test-secret"),
    )


@pytest.mark.parametrize(
    ("mime", "data", "extension"),
    [
        ("image/jpeg", b"\xff\xd8\xff\xe0demo", ".jpg"),
        ("image/png", b"\x89PNG\r\n\x1a\ndemo", ".png"),
        ("image/webp", b"RIFF1234WEBPdemo", ".webp"),
        ("image/avif", b"\x00\x00\x00\x18ftypavif\x00\x00\x00\x00", ".avif"),
    ],
    ids=["jpeg", "png", "webp", "avif"],
)
async def test_upload_read_and_delete_images(mime, data, extension) -> None:
    s3 = FakeS3()
    storage = S3FileStorage(settings=storage_settings(), client=s3)

    url = await storage.upload_image(data, "recipes/1234-abcd", mime)

    assert url.startswith("http://localhost:9000/culinary-blog/recipes/1234-abcd/")
    assert url.endswith(extension)
    assert (await storage.read(url)).data == data
    assert (await storage.read(url)).content_type == mime
    await storage.delete(url)
    await storage.delete(url)  # missing objects are safe to delete again
    assert s3.objects == {}
    with pytest.raises(StorageNotFound):
        await storage.read(url)


@pytest.mark.parametrize(
    ("data", "mime"),
    [
        (b"not-image", "image/jpeg"),
        (b"\xff\xd8\xff", "text/plain"),
        (b"\xff\xd8\xff" + b"a" * MAX_IMAGE_BYTES, "image/jpeg"),
        (b"", "image/png"),
    ],
    ids=["wrong-signature", "wrong-mime", "oversized", "empty"],
)
async def test_invalid_images_are_rejected_before_s3(data, mime) -> None:
    s3 = FakeS3()
    storage = S3FileStorage(settings=storage_settings(), client=s3)

    with pytest.raises(InvalidImage):
        await storage.upload_image(data, "recipes/1", mime)
    assert s3.objects == {}


async def test_untrusted_folder_and_url_cannot_access_s3() -> None:
    s3 = FakeS3()
    storage = S3FileStorage(settings=storage_settings(), client=s3)
    with pytest.raises(InvalidImage):
        await storage.upload_image(b"\xff\xd8\xff", "../secrets", "image/jpeg")
    with pytest.raises(InvalidImage):
        await storage.delete("http://evil.example/culinary-blog/recipes/1/file.jpg")
    with pytest.raises(InvalidImage):
        await storage.read("http://localhost:9000/culinary-blog/recipes/%2e%2e/password.jpg")


async def test_s3_failure_becomes_storage_error() -> None:
    s3 = FakeS3()
    s3.fail = True
    storage = S3FileStorage(settings=storage_settings(), client=s3)
    with pytest.raises(StorageUnavailable):
        await storage.upload_image(b"\xff\xd8\xff", "recipes/1", "image/jpeg")


async def test_transient_s3_errors_are_retried() -> None:
    s3 = FakeS3()
    s3.transient_failures = 2
    storage = S3FileStorage(settings=storage_settings(), client=s3)

    url = await storage.upload_image(b"\xff\xd8\xff", "recipes/1", "image/jpeg")

    assert s3.transient_failures == 0
    assert (await storage.read(url)).data == b"\xff\xd8\xff"


async def test_missing_bucket_during_upload_is_service_error() -> None:
    class MissingBucketS3(FakeS3):
        def put_object(self, **_kwargs) -> None:
            raise ClientError(
                {"Error": {"Code": "404", "Message": "Missing bucket"}}, "PutObject"
            )

    storage = S3FileStorage(settings=storage_settings(), client=MissingBucketS3())
    with pytest.raises(StorageUnavailable):
        await storage.upload_image(b"\xff\xd8\xff", "recipes/1", "image/jpeg")


async def test_variant_keys_are_stable_and_confined_to_recipe_bucket() -> None:
    s3 = FakeS3()
    storage = S3FileStorage(settings=storage_settings(), client=s3)
    recipe_id, image_id = uuid.uuid4(), uuid.uuid4()
    data = b"RIFF1234WEBPdemo"

    first = await storage.upload_variant(data, recipe_id, image_id, "medium")
    second = await storage.upload_variant(data, recipe_id, image_id, "medium")

    assert first == second
    assert (await storage.read(first)).data == data
    assert len(s3.objects) == 1
    with pytest.raises(InvalidImage):
        await storage.upload_variant(data, recipe_id, image_id, "../../secret")
    await storage.delete_variant(recipe_id, image_id, "medium")
    await storage.delete_variant(recipe_id, image_id, "medium")
    assert s3.objects == {}
