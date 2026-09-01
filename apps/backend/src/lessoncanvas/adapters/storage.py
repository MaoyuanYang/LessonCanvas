import io

import boto3
from botocore.client import Config as BotoConfig

from lessoncanvas.settings import get_settings


class StorageAdapter:
    def __init__(self, bucket: str | None = None) -> None:
        settings = get_settings()
        self._bucket = bucket or settings.s3_bucket_sources
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            config=BotoConfig(signature_version="s3v4"),
            region_name="us-east-1",
        )

    def ensure_bucket(self) -> None:
        try:
            self._client.head_bucket(Bucket=self._bucket)
            return
        except Exception:
            pass
        try:
            self._client.create_bucket(Bucket=self._bucket)
        except Exception:
            # Concurrent first-writer bucket creation: the bucket exists if
            # the other writer won the race; anything else is a real failure.
            self._client.head_bucket(Bucket=self._bucket)

    def put(self, key: str, data: bytes) -> None:
        self.ensure_bucket()
        self._client.put_object(Bucket=self._bucket, Key=key, Body=data)

    def get(self, key: str) -> bytes:
        response = self._client.get_object(Bucket=self._bucket, Key=key)
        return response["Body"].read()

    def exists(self, key: str) -> bool:
        """F011 deletion-completeness verification: object presence probe."""
        try:
            self._client.head_object(Bucket=self._bucket, Key=key)
            return True
        except Exception:
            return False

    def list_prefix(self, prefix: str) -> list[str]:
        """F011 deletion-completeness verification: keys under a prefix."""
        keys: list[str] = []
        token: str | None = None
        while True:
            kwargs = {"Bucket": self._bucket, "Prefix": prefix}
            if token:
                kwargs["ContinuationToken"] = token
            response = self._client.list_objects_v2(**kwargs)
            keys.extend(item["Key"] for item in response.get("Contents", []))
            if not response.get("IsTruncated"):
                return keys
            token = response["NextContinuationToken"]

    def delete(self, key: str) -> None:
        self._client.delete_object(Bucket=self._bucket, Key=key)


def read_all(stream: io.BytesIO) -> bytes:
    return stream.read()
