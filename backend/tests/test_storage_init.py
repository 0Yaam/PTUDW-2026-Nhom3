"""Local bucket setup creates an anonymous-read policy only after readiness."""

import json
from types import SimpleNamespace

from botocore.exceptions import ClientError

from culinary_blog_api.storage import init_bucket


def test_bucket_initializer_creates_bucket_and_public_read_policy(monkeypatch) -> None:
    calls = []

    class FakeClient:
        def head_bucket(self, *, Bucket) -> None:
            calls.append(("head", Bucket))
            raise ClientError({"Error": {"Code": "404", "Message": "Not found"}}, "HeadBucket")

        def create_bucket(self, *, Bucket) -> None:
            calls.append(("create", Bucket))

        def put_bucket_policy(self, *, Bucket, Policy) -> None:
            calls.append(("policy", Bucket, json.loads(Policy)))

    monkeypatch.setattr(
        init_bucket,
        "S3FileStorage",
        lambda: SimpleNamespace(
            client=FakeClient(), settings=SimpleNamespace(minio_bucket="culinary-blog")
        ),
    )

    init_bucket.ensure_bucket()

    assert calls[0:2] == [("head", "culinary-blog"), ("create", "culinary-blog")]
    policy = calls[2][2]
    assert policy["Statement"][0]["Action"] == "s3:GetObject"
    assert policy["Statement"][0]["Resource"] == "arn:aws:s3:::culinary-blog/*"
