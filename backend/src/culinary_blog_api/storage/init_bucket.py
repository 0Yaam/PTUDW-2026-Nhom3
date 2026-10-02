"""Prepare the local MinIO bucket and anonymous-read policy once per startup."""

import json
import time

import structlog
from botocore.exceptions import BotoCoreError, ClientError

from .service import S3FileStorage

logger = structlog.get_logger()


def ensure_bucket() -> None:
    storage = S3FileStorage()
    client = storage.client
    bucket = storage.settings.minio_bucket
    for attempt in range(30):
        try:
            try:
                client.head_bucket(Bucket=bucket)
            except ClientError as error:
                if error.response.get("Error", {}).get("Code") not in ("404", "NoSuchBucket"):
                    raise
                client.create_bucket(Bucket=bucket)
            policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": "*",
                        "Action": "s3:GetObject",
                        "Resource": f"arn:aws:s3:::{bucket}/*",
                    }
                ],
            }
            client.put_bucket_policy(Bucket=bucket, Policy=json.dumps(policy))
            logger.info("storage_bucket_ready", bucket=bucket)
            return
        except (BotoCoreError, ClientError, OSError) as error:
            logger.warning(
                "storage_bucket_waiting", attempt=attempt + 1, error_type=type(error).__name__
            )
            time.sleep(2)
    raise RuntimeError("MinIO bucket initialization failed after 30 attempts")


if __name__ == "__main__":
    ensure_bucket()
