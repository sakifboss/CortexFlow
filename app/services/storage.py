"""
Object storage service (S3-compatible — MinIO in dev, S3 in prod).

Responsibilities:
  - bucket provisioning on startup
  - multipart uploads (large PDFs)
  - presigned download URLs (private objects served to the UI)
  - content-addressed keys (sha256) for dedup
"""
from __future__ import annotations

import hashlib
from io import BytesIO

from loguru import logger
from minio import Minio
from minio.error import S3Error

from app.core.config import settings


class StorageService:
    def __init__(self) -> None:
        self.client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
        self.bucket = settings.minio_bucket

    def ensure_bucket(self) -> None:
        try:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
                logger.info("Created MinIO bucket '{}'.", self.bucket)
        except S3Error as exc:
            logger.error("MinIO bucket setup failed: {}", exc)

    def key_for(self, workspace_id: str, filename: str, checksum: str) -> str:
        return f"workspaces/{workspace_id}/{checksum}/{filename}"

    def upload_bytes(self, key: str, data: bytes, *, content_type: str, metadata: dict | None = None) -> str:
        self.client.put_object(
            bucket_name=self.bucket,
            object_name=key,
            data=BytesIO(data),
            length=len(data),
            content_type=content_type,
            metadata=metadata or {},
        )
        return key

    def download(self, key: str) -> bytes:
        obj = self.client.get_object(self.bucket, key)
        try:
            return obj.read()
        finally:
            obj.close()
            obj.release_conn()

    def presigned_url(self, key: str, expires_seconds: int = 3600) -> str:
        from datetime import timedelta

        return self.client.presigned_get_object(self.bucket, key, expires=timedelta(seconds=expires_seconds))

    def delete(self, key: str) -> None:
        try:
            self.client.remove_object(self.bucket, key)
        except S3Error as exc:
            logger.warning("Failed to delete object {}: {}", key, exc)

    @staticmethod
    def checksum(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()


storage = StorageService()
