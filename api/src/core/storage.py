# Storage abstraction — ARCH-002 Patch, Fix 1
# Provides local filesystem and S3/R2-compatible object storage backends.
from __future__ import annotations

import abc
from pathlib import Path

import structlog

logger = structlog.get_logger()


class BaseStorage(abc.ABC):
    """Abstract interface for report file storage."""

    @abc.abstractmethod
    async def upload(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        """Upload data and return the storage key."""
        ...

    @abc.abstractmethod
    async def download(self, key: str) -> bytes:
        """Download and return file contents."""
        ...

    @abc.abstractmethod
    async def exists(self, key: str) -> bool:
        """Check whether a key exists in storage."""
        ...

    @abc.abstractmethod
    async def get_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        """Return a presigned/temporary URL for the object."""
        ...


class LocalStorage(BaseStorage):
    """Store report files on the local filesystem under REPORT_STORAGE_PATH."""

    def __init__(self, base_path: str) -> None:
        self._base = Path(base_path)

    def _resolve(self, key: str) -> Path:
        return self._base / key

    async def upload(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        path = self._resolve(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        logger.debug("local_storage_upload", key=key, size=len(data))
        return key

    async def download(self, key: str) -> bytes:
        return self._resolve(key).read_bytes()

    async def exists(self, key: str) -> bool:
        return self._resolve(key).exists()

    async def get_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        # Local storage has no presigned URLs; return the filesystem path.
        return str(self._resolve(key))


class S3Storage(BaseStorage):
    """Store report files in an S3-compatible bucket (AWS S3 / Cloudflare R2)."""

    def __init__(
        self,
        bucket: str,
        region: str = "us-east-1",
        endpoint_url: str | None = None,
        access_key_id: str | None = None,
        secret_access_key: str | None = None,
    ) -> None:
        self._bucket = bucket
        self._region = region
        self._endpoint_url = endpoint_url
        self._access_key_id = access_key_id
        self._secret_access_key = secret_access_key

    def _session_kwargs(self) -> dict:
        kwargs: dict = {}
        if self._access_key_id:
            kwargs["aws_access_key_id"] = self._access_key_id
        if self._secret_access_key:
            kwargs["aws_secret_access_key"] = self._secret_access_key
        return kwargs

    def _client_kwargs(self) -> dict:
        kwargs: dict = {"region_name": self._region}
        if self._endpoint_url:
            kwargs["endpoint_url"] = self._endpoint_url
        return kwargs

    async def upload(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        import aioboto3

        session = aioboto3.Session(**self._session_kwargs())
        async with session.client("s3", **self._client_kwargs()) as s3:
            await s3.put_object(Bucket=self._bucket, Key=key, Body=data, ContentType=content_type)
        logger.debug("s3_storage_upload", bucket=self._bucket, key=key, size=len(data))
        return key

    async def download(self, key: str) -> bytes:
        import aioboto3

        session = aioboto3.Session(**self._session_kwargs())
        async with session.client("s3", **self._client_kwargs()) as s3:
            resp = await s3.get_object(Bucket=self._bucket, Key=key)
            return await resp["Body"].read()

    async def exists(self, key: str) -> bool:
        import aioboto3

        session = aioboto3.Session(**self._session_kwargs())
        async with session.client("s3", **self._client_kwargs()) as s3:
            try:
                await s3.head_object(Bucket=self._bucket, Key=key)
                return True
            except s3.exceptions.ClientError:
                return False
            except Exception:
                return False

    async def get_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        import aioboto3

        session = aioboto3.Session(**self._session_kwargs())
        async with session.client("s3", **self._client_kwargs()) as s3:
            return await s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": self._bucket, "Key": key},
                ExpiresIn=expires_in,
            )


def get_storage() -> BaseStorage:
    """Factory: return the storage backend based on STORAGE_BACKEND env var."""
    from src.core.config import get_settings

    settings = get_settings()
    backend = settings.STORAGE_BACKEND.lower()

    if backend == "s3":
        return S3Storage(
            bucket=settings.S3_BUCKET,
            region=settings.S3_REGION,
            endpoint_url=settings.S3_ENDPOINT_URL or None,
            access_key_id=settings.S3_ACCESS_KEY_ID or None,
            secret_access_key=settings.S3_SECRET_ACCESS_KEY or None,
        )

    # Default: local filesystem
    return LocalStorage(settings.REPORT_STORAGE_PATH)
