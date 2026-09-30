"""File storage adapter (README section 6.1: MinIO / S3).

* ``LocalStorage``  — filesystem under ``settings.data_dir`` (default for local dev,
  no external services needed).
* ``S3Storage``     — MinIO / S3 via boto3 (used in Docker Compose).

Both store opaque ``storage_key`` strings; ``open_stream`` is used by the API to
serve uploaded files back to the frontend.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import BinaryIO, Protocol

from app.shared.config import Settings, get_settings
from app.shared.errors import AppError, ErrorCode


class Storage(Protocol):
    def put(self, key: str, stream: BinaryIO, *, length: int | None = None) -> str: ...
    def open_stream(self, key: str) -> BinaryIO: ...
    def exists(self, key: str) -> bool: ...


class LocalStorage:
    def __init__(self, root: str | Path) -> None:
        self._root = Path(root).resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        candidate = (self._root / key).resolve()
        if not candidate.is_relative_to(self._root):
            raise AppError(ErrorCode.VALIDATION_ERROR, "Invalid storage key.", status_code=422)
        return candidate

    def put(self, key: str, stream: BinaryIO, *, length: int | None = None) -> str:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as target:
            shutil.copyfileobj(stream, target)
        return key

    def open_stream(self, key: str) -> BinaryIO:
        path = self._path(key)
        if not path.exists():
            raise AppError(ErrorCode.NOT_FOUND, "File not found in storage.", status_code=404)
        return path.open("rb")

    def exists(self, key: str) -> bool:
        return self._path(key).exists()


class S3Storage:
    def __init__(self, settings: Settings) -> None:
        import boto3  # imported lazily so local dev does not require it at import time

        self._client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url or None,
        )
        self._bucket = settings.s3_bucket

    def put(self, key: str, stream: BinaryIO, *, length: int | None = None) -> str:
        extra = {"ContentLength": length} if length is not None else {}
        self._client.upload_fileobj(stream, self._bucket, key, ExtraArgs=extra or None)
        return key

    def open_stream(self, key: str) -> BinaryIO:
        import io

        buffer = io.BytesIO()
        self._client.download_fileobj(self._bucket, key, buffer)
        buffer.seek(0)
        return buffer

    def exists(self, key: str) -> bool:
        try:
            self._client.head_object(Bucket=self._bucket, Key=key)
            return True
        except Exception:
            return False


_storage: Storage | None = None


def get_storage(settings: Settings | None = None) -> Storage:
    global _storage
    if _storage is None:
        settings = settings or get_settings()
        if settings.storage_mode == "s3":
            _storage = S3Storage(settings)
        else:
            _storage = LocalStorage(settings.data_dir)
    return _storage


def reset_storage() -> None:
    """Test helper."""
    global _storage
    _storage = None
