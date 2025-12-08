from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from sage.studio.config.backend.api import app
from sage.studio.services.file_upload_service import FileMetadata

client = TestClient(app)


@pytest.fixture
def mock_upload_service():
    with patch("sage.studio.config.backend.api.get_file_upload_service") as mock_get:
        service = MagicMock()
        mock_get.return_value = service
        yield service


def test_upload_file(mock_upload_service):
    mock_upload_service.upload_file = AsyncMock(
        return_value=FileMetadata(
            file_id="123",
            filename="123_test.txt",
            original_name="test.txt",
            file_type=".txt",
            size_bytes=4,
            upload_time="2023-01-01T00:00:00",
            path="/tmp/123_test.txt",
            indexed=False,
        )
    )

    files = {"file": ("test.txt", b"test", "text/plain")}
    response = client.post("/api/uploads", files=files)

    assert response.status_code == 200
    data = response.json()
    assert data["file_id"] == "123"
    assert data["original_name"] == "test.txt"

    mock_upload_service.upload_file.assert_called_once()


def test_list_files(mock_upload_service):
    mock_upload_service.list_files.return_value = [
        FileMetadata(
            file_id="123",
            filename="123_test.txt",
            original_name="test.txt",
            file_type=".txt",
            size_bytes=4,
            upload_time="2023-01-01T00:00:00",
            path="/tmp/123_test.txt",
            indexed=False,
        )
    ]

    response = client.get("/api/uploads")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["file_id"] == "123"


def test_delete_file(mock_upload_service):
    mock_upload_service.delete_file.return_value = True

    response = client.delete("/api/uploads/123")
    assert response.status_code == 200
    assert response.json()["success"] is True

    mock_upload_service.delete_file.assert_called_with("123")


def test_delete_file_not_found(mock_upload_service):
    mock_upload_service.delete_file.return_value = False

    response = client.delete("/api/uploads/999")
    assert response.status_code == 404
