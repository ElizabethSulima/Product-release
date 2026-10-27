import io
from unittest.mock import MagicMock

import pytest
from fastapi import status
from httpx import AsyncClient

pytestmark = pytest.mark.anyio


async def test_upload_file_success(
    client: AsyncClient, mock_minio_service: MagicMock
):
    """Тест успешной загрузки файла в валидный бакет"""
    mock_minio_service.upload_file_bytes.return_value = (
        "https://minio.local/reports/test-file.xlsx",
        "2026-11-03T12:00:00Z",
    )

    file_content = b"test file content"
    files = {
        "file": (
            "test.xlsx",
            io.BytesIO(file_content),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    }

    response = await client.post("/api/v1/files/upload/reports", files=files)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["message"] == "Файл успешно загружен"
    assert data["bucket"] == "reports"
    assert data["object_name"].endswith(".xlsx")
    assert (
        data["presigned_url"] == "https://minio.local/reports/test-file.xlsx"
    )

    mock_minio_service.upload_file_bytes.assert_called_once()


@pytest.mark.asyncio
async def test_upload_file_invalid_bucket(client: AsyncClient):
    """Тест загрузки файла в недопустимый бакет (должен вернуть 400)"""
    file_content = b"test file content"
    files = {"file": ("test.txt", io.BytesIO(file_content), "text/plain")}

    response = await client.post(
        "/api/v1/files/upload/invalid-bucket", files=files
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "Недопустимый бакет"


async def test_upload_file_minio_error(
    client: AsyncClient, mock_minio_service: MagicMock
):
    """Тест обработки ошибки при загрузке файла в MinIO (должен вернуть 500)"""
    mock_minio_service.upload_file_bytes.side_effect = Exception(
        "MinIO connection failed"
    )

    file_content = b"test file content"
    files = {"file": ("test.txt", io.BytesIO(file_content), "text/plain")}

    response = await client.post("/api/v1/files/upload/reports", files=files)

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "MinIO connection failed" in response.json()["detail"]


async def test_list_files_success(
    client: AsyncClient, mock_minio_service: MagicMock
):
    """Тест успешного получения списка файлов"""
    mock_minio_service.list_files.return_value = [
        {
            "object_name": "file1.xlsx",
            "size": 1024,
            "last_modified": "2026-10-27T10:00:00Z",
            "is_dir": False,
        },
    ]

    response = await client.get("/api/v1/files/list/reports")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["bucket"] == "reports"
    assert len(data["files"]) == 1
    assert data["files"][0]["object_name"] == "file1.xlsx"

    mock_minio_service.list_files.assert_called_once_with(
        bucket="reports", prefix=""
    )


async def test_list_files_invalid_bucket(client: AsyncClient):
    """
    Тест получения списка файлов из недопустимого бакета (должен вернуть 400)
    """
    response = await client.get("/api/v1/files/list/invalid-bucket")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "Недопустимый бакет"


async def test_get_download_url_success(
    client: AsyncClient, mock_minio_service: MagicMock
):
    """Тест успешного получения presigned URL для скачивания"""
    mock_minio_service.client.presigned_get_object.return_value = (
        "https://minio.local/reports/test-file.xlsx?signature=abc123"
    )

    response = await client.get(
        "/api/v1/files/download/reports/test-file.xlsx"
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert (
        data["presigned_url"]
        == "https://minio.local/reports/test-file.xlsx?signature=abc123"
    )

    mock_minio_service.client.presigned_get_object.assert_called_once_with(
        bucket_name="reports",
        object_name="test-file.xlsx",
    )


async def test_get_download_url_file_not_found(
    client: AsyncClient, mock_minio_service: MagicMock
):
    """Тест получения URL для несуществующего файла (должен вернуть 404)"""
    mock_minio_service.client.presigned_get_object.side_effect = Exception(
        "NoSuchKey"
    )

    response = await client.get(
        "/api/v1/files/download/reports/nonexistent.xlsx"
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Файл не найден или ошибка доступа"


async def test_delete_file_success(
    client: AsyncClient, mock_minio_service: MagicMock
):
    """Тест успешного удаления файла"""
    response = await client.delete("/api/v1/files/reports/test-file.xlsx")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["message"] == "Файл успешно удален"

    mock_minio_service.delete_file.assert_called_once_with(
        bucket="reports", object_name="test-file.xlsx"
    )


async def test_delete_file_minio_error(
    client: AsyncClient, mock_minio_service: MagicMock
):
    """Тест обработки ошибки при удалении файла (должен вернуть 500)"""
    mock_minio_service.delete_file.side_effect = Exception("Permission denied")

    response = await client.delete("/api/v1/files/reports/test-file.xlsx")

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "Permission denied" in response.json()["detail"]


async def test_list_files_with_prefix(
    client: AsyncClient, mock_minio_service: MagicMock
):
    """Тест получения списка файлов с фильтром по префиксу"""
    mock_minio_service.list_files.return_value = [
        {
            "object_name": "exports/report_2026_10.xlsx",
            "size": 1024,
            "last_modified": None,
            "is_dir": False,
        },
    ]

    response = await client.get("/api/v1/files/list/exports?prefix=exports/")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["bucket"] == "exports"
    assert len(data["files"]) == 1

    mock_minio_service.list_files.assert_called_once_with(
        bucket="exports", prefix="exports/"
    )


async def test_list_files_minio_error(
    client: AsyncClient, mock_minio_service: MagicMock
):
    """Тест обработки ошибки при получении списка файлов (должен вернуть 500)"""
    mock_minio_service.list_files.side_effect = Exception("MinIO timeout")

    response = await client.get("/api/v1/files/list/reports")

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "MinIO timeout" in response.json()["detail"]
