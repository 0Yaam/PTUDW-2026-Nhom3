"""Validate recipe images and store them through an S3-compatible client.

The public URL is a reference, never a trusted S3 key. Reads and deletes only
accept URLs generated under this adapter's configured public bucket prefix.
"""

import asyncio
import re
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol, TypeVar
from urllib.parse import quote, unquote, urlsplit

import boto3
import structlog
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import UploadFile

from ..config import Settings, get_settings

logger = structlog.get_logger()
MAX_IMAGE_BYTES = 5 * 1024 * 1024
RETRY_DELAYS = (0.2, 0.4)
T = TypeVar("T")
MIME_EXTENSIONS = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/avif": "avif",
}
FOLDER_PATTERN = re.compile(r"[A-Za-z0-9_-]+(?:/[A-Za-z0-9_-]+)*\Z")
OBJECT_KEY_PATTERN = re.compile(
    r"(?:[A-Za-z0-9_-]+(?:/[A-Za-z0-9_-]+)*/[0-9a-f]{32}\.(?:jpg|png|webp|avif)"
    r"|recipes/[0-9a-f-]{36}/[0-9a-f-]{36}/(?:medium|thumbnail)\.webp)\Z"
)


class InvalidImage(ValueError):
    """The file, folder, or object URL is invalid (HTTP 400 at the API edge)."""


class StorageNotConfigured(RuntimeError):
    """Object storage environment settings are missing."""


class StorageUnavailable(RuntimeError):
    """The configured object store did not complete an operation (HTTP 503)."""


class StorageNotFound(FileNotFoundError):
    """An image URL belongs to this bucket, but its object is missing."""


@dataclass(frozen=True)
class StoredFile:
    data: bytes
    content_type: str


class FileStorage(Protocol):
    """Contract for #43 image APIs; no image routes are owned by this module."""

    async def upload_file(self, file: UploadFile, folder: str) -> str: ...

    async def upload_image(self, data: bytes, folder: str, content_type: str) -> str: ...

    async def read(self, file_url: str) -> StoredFile: ...

    async def delete(self, file_url: str) -> None: ...

    async def upload_variant(
        self, data: bytes, recipe_id: uuid.UUID, image_id: uuid.UUID, size: str
    ) -> str: ...

    async def delete_variant(
        self, recipe_id: uuid.UUID, image_id: uuid.UUID, size: str
    ) -> None: ...


def validate_image(data: bytes, content_type: str) -> str:
    """Check claimed MIME, size, and file signature before any S3 call."""
    mime = content_type.lower().split(";", 1)[0].strip()
    extension = MIME_EXTENSIONS.get(mime)
    if extension is None:
        raise InvalidImage("Only JPEG, PNG, WebP, and AVIF images are accepted.")
    if not data or len(data) > MAX_IMAGE_BYTES:
        raise InvalidImage("Image must be non-empty and at most 5 MB.")
    matches = {
        "image/jpeg": lambda: data.startswith(b"\xff\xd8\xff"),
        "image/png": lambda: data.startswith(b"\x89PNG\r\n\x1a\n"),
        "image/webp": lambda: len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP",
        "image/avif": lambda: len(data) >= 16
        and data[4:8] == b"ftyp"
        and (data[8:12] in (b"avif", b"avis") or b"avif" in data[16:32]),
    }
    if not matches[mime]():
        raise InvalidImage("Image signature does not match its MIME type.")
    return extension


class S3FileStorage:
    """Async facade for boto3, with a restricted public URL/key contract."""

    def __init__(self, settings: Settings | None = None, client: Any | None = None) -> None:
        self.settings = settings or get_settings()
        if not all(
            (
                self.settings.minio_endpoint,
                self.settings.minio_public_url,
                self.settings.minio_access_key,
                self.settings.minio_secret_key.get_secret_value(),
                self.settings.minio_bucket,
            )
        ):
            raise StorageNotConfigured("MinIO connection settings are missing.")
        self.client = client or boto3.client(
            "s3",
            endpoint_url=self.settings.minio_endpoint,
            aws_access_key_id=self.settings.minio_access_key,
            aws_secret_access_key=self.settings.minio_secret_key.get_secret_value(),
            region_name=self.settings.minio_region,
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
        )

    def _object_key(self, file_url: str) -> str:
        base = urlsplit(self.settings.minio_public_url.rstrip("/"))
        target = urlsplit(file_url)
        prefix = f"{base.path.rstrip('/')}/{self.settings.minio_bucket}/"
        if (
            target.scheme != base.scheme
            or target.netloc != base.netloc
            or target.query
            or target.fragment
            or not target.path.startswith(prefix)
        ):
            raise InvalidImage("File URL does not belong to the configured bucket.")
        key = unquote(target.path[len(prefix) :])
        if not OBJECT_KEY_PATTERN.fullmatch(key):
            raise InvalidImage("File URL contains an invalid object key.")
        return key

    def _variant_key(self, recipe_id: uuid.UUID, image_id: uuid.UUID, size: str) -> str:
        if size not in {"medium", "thumbnail"}:
            raise InvalidImage("Unknown recipe image variant.")
        return f"recipes/{recipe_id}/{image_id}/{size}.webp"

    def _public_url(self, key: str) -> str:
        return (
            f"{self.settings.minio_public_url.rstrip('/')}/"
            f"{self.settings.minio_bucket}/{quote(key, safe='/')}"
        )

    async def _run(self, action: Callable[[], T], operation: str, key: str) -> T:
        """Retry transient S3 failures twice, then surface a stable error."""
        for attempt in range(len(RETRY_DELAYS) + 1):
            try:
                return await asyncio.to_thread(action)
            except ClientError as error:
                code = error.response.get("Error", {}).get("Code", "")
                status = error.response.get("ResponseMetadata", {}).get("HTTPStatusCode", 0)
                if code in ("NoSuchKey", "404"):
                    if operation == "delete":
                        return None  # type: ignore[return-value]
                    if operation == "read":
                        raise StorageNotFound("Stored image was not found.") from error
                retryable = status >= 500 or code in ("SlowDown", "Throttling")
                failure: Exception = error
            except (BotoCoreError, OSError) as error:
                retryable = True
                failure = error
            if not retryable or attempt == len(RETRY_DELAYS):
                logger.error(
                    "storage_operation_failed",
                    operation=operation,
                    object_key=key,
                    attempts=attempt + 1,
                    error_type=type(failure).__name__,
                )
                raise StorageUnavailable("Image storage is unavailable.") from failure
            await asyncio.sleep(RETRY_DELAYS[attempt])
        raise AssertionError("unreachable")

    async def upload_image(self, data: bytes, folder: str, content_type: str) -> str:
        extension = validate_image(data, content_type)
        if not FOLDER_PATTERN.fullmatch(folder):
            raise InvalidImage("Invalid image folder.")
        key = f"{folder}/{uuid.uuid4().hex}.{extension}"
        mime = content_type.lower().split(";", 1)[0].strip()
        await self._run(
            lambda: self.client.put_object(
                Bucket=self.settings.minio_bucket, Key=key, Body=data, ContentType=mime
            ),
            "upload",
            key,
        )
        return self._public_url(key)

    async def upload_variant(
        self, data: bytes, recipe_id: uuid.UUID, image_id: uuid.UUID, size: str
    ) -> str:
        """Overwrite a deterministic key so a retried resize cannot make duplicates."""
        validate_image(data, "image/webp")
        key = self._variant_key(recipe_id, image_id, size)
        await self._run(
            lambda: self.client.put_object(
                Bucket=self.settings.minio_bucket,
                Key=key,
                Body=data,
                ContentType="image/webp",
            ),
            "upload",
            key,
        )
        return self._public_url(key)

    async def delete_variant(self, recipe_id: uuid.UUID, image_id: uuid.UUID, size: str) -> None:
        key = self._variant_key(recipe_id, image_id, size)
        await self._run(
            lambda: self.client.delete_object(Bucket=self.settings.minio_bucket, Key=key),
            "delete",
            key,
        )

    async def upload_file(self, file: UploadFile, folder: str) -> str:
        """Bound multipart reads to 5 MB + 1 before passing bytes to storage."""
        data = await file.read(MAX_IMAGE_BYTES + 1)
        return await self.upload_image(data, folder, file.content_type or "")

    async def read(self, file_url: str) -> StoredFile:
        key = self._object_key(file_url)

        def fetch() -> StoredFile:
            response = self.client.get_object(Bucket=self.settings.minio_bucket, Key=key)
            body = response["Body"]
            try:
                data = body.read(MAX_IMAGE_BYTES + 1)
            finally:
                body.close()
            if len(data) > MAX_IMAGE_BYTES:
                raise StorageUnavailable("Stored image exceeds the 5 MB limit.")
            return StoredFile(data=data, content_type=response["ContentType"])

        return await self._run(fetch, "read", key)

    async def delete(self, file_url: str) -> None:
        """S3 delete is idempotent, including when the object is already absent."""
        key = self._object_key(file_url)
        await self._run(
            lambda: self.client.delete_object(Bucket=self.settings.minio_bucket, Key=key),
            "delete",
            key,
        )
