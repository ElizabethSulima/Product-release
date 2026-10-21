import io
import os
from datetime import UTC, datetime, timedelta
from typing import Any

from minio import Minio

from src.core.config import config


class MinIOService:
    def __init__(self) -> None:
        self.client = Minio(
            endpoint=config.MINIO_ENDPOINT,
            access_key=config.MINIO_ACCESS_KEY,
            secret_key=config.MINIO_SECRET_KEY,
            secure=config.MINIO_SECURE,
        )

    def ensure_bucket_exists(self, bucket_name: str) -> None:
        """Создает бакет, если его нет"""
        if not self.client.bucket_exists(bucket_name):
            self.client.make_bucket(bucket_name)

    def upload_file_bytes(
        self,
        bucket: str,
        file_bytes: bytes,
        object_name: str,
        content_type: str,
        expires_days: int = 7,
    ) -> tuple[str, str]:
        """
        Загрузить файл из байтов (в памяти) в MinIO.
        Возвращает кортеж: (pre-signed URL, дата истечения ISO format)
        """
        self.ensure_bucket_exists(bucket)

        file_size = len(file_bytes)

        self.client.put_object(
            bucket_name=bucket,
            object_name=object_name,
            data=io.BytesIO(file_bytes),
            length=file_size,
            content_type=content_type,
        )
        url = self.client.presigned_get_object(
            bucket_name=bucket,
            object_name=object_name,
            expires=timedelta(days=expires_days),
        )

        expires_at = (
            datetime.now(UTC) + timedelta(days=expires_days)
        ).isoformat()

        return url, expires_at

    def upload_file(
        self,
        bucket: str,
        file_path: str,
        object_name: str | None = None,
        expires_days: int = 7,
    ) -> str:
        if object_name is None:
            object_name = os.path.basename(file_path)
        self.client.fput_object(
            bucket_name=bucket,
            object_name=object_name,
            file_path=file_path,
            content_type=self._get_content_type(file_path),
        )
        return self.client.presigned_get_object(
            bucket_name=bucket,
            object_name=object_name,
            expires=timedelta(days=expires_days),
        )

    def download_file(
        self, bucket: str, object_name: str, file_path: str
    ) -> None:
        self.client.fget_object(
            bucket_name=bucket, object_name=object_name, file_path=file_path
        )

    def delete_file(self, bucket: str, object_name: str) -> None:
        self.client.remove_object(bucket, object_name)

    def list_files(
        self, bucket: str, prefix: str = ""
    ) -> list[dict[str, Any]]:
        """Возвращает список объектов в бакете"""
        self.ensure_bucket_exists(bucket)
        objects = self.client.list_objects(
            bucket_name=bucket, prefix=prefix, recursive=True
        )

        files = []
        for obj in objects:
            files.append(
                {
                    "object_name": obj.object_name,
                    "size": obj.size,
                    "last_modified": (
                        obj.last_modified.isoformat()
                        if obj.last_modified
                        else None
                    ),
                    "is_dir": obj.is_dir,
                }
            )
        return files

    def _get_content_type(self, file_path: str) -> str:
        ext = os.path.splitext(file_path)[1].lower()
        content_types = {
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ".xls": "application/vnd.ms-excel",
            ".csv": "text/csv",
            ".pdf": "application/pdf",
            ".json": "application/json",
        }
        return content_types.get(ext, "application/octet-stream")


minio_service = MinIOService()
