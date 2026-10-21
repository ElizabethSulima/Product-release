import os
import uuid
from typing import Any

from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status

from src.storage.minio_service import minio_service

router = APIRouter(prefix="/files", tags=["Files"])


@router.post("/upload/{bucket}")
async def upload_file(
    bucket: str, file: UploadFile = File(...)
) -> dict[str, Any]:
    if bucket not in ["reports", "exports", "imports"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Недопустимый бакет",
        )

    ext = os.path.splitext(file.filename or "")[1].lower()
    object_name = f"{uuid.uuid4()}{ext}"

    file_bytes = await file.read()

    try:
        url, expires_at = minio_service.upload_file_bytes(
            bucket=bucket,
            file_bytes=file_bytes,
            object_name=object_name,
            content_type=file.content_type or "application/octet-stream",
            expires_days=7,
        )
        return {
            "message": "Файл успешно загружен",
            "bucket": bucket,
            "object_name": object_name,
            "presigned_url": url,
            "expires_at": expires_at,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        ) from e


@router.get("/list/{bucket}")
async def list_files(bucket: str, prefix: str = Query("")) -> dict[str, Any]:
    if bucket not in ["reports", "exports", "imports"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Недопустимый бакет",
        )

    try:
        files = minio_service.list_files(bucket=bucket, prefix=prefix)
        return {"bucket": bucket, "files": files}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        ) from e


@router.get("/download/{bucket}/{object_name:path}")
async def get_download_url(bucket: str, object_name: str) -> dict[str, Any]:
    try:
        url = minio_service.client.presigned_get_object(
            bucket_name=bucket,
            object_name=object_name,
        )
        return {"presigned_url": url}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Файл не найден или ошибка доступа",
        ) from e


@router.delete("/{bucket}/{object_name:path}")
async def delete_file(bucket: str, object_name: str) -> dict[str, Any]:
    try:
        minio_service.delete_file(bucket=bucket, object_name=object_name)
        return {"message": "Файл успешно удален"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        ) from e
