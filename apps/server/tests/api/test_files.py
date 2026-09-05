"""Tests for File upload/download REST endpoints."""

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import (
    get_current_user,
    get_db_session,
    get_file_upload_service,
    get_redis,
)
from app.core.config import settings
from app.core.exceptions import NotFoundError
from app.main import app
from app.services.file_upload import FileUploadService


class MockUser:
    """Mock authenticated user."""

    def __init__(self):
        self.id = uuid4()
        self.email = "test@example.com"
        self.full_name = "Test User"
        self.is_active = True
        self.role = "user"


@pytest.fixture
def mock_user():
    return MockUser()


@pytest.fixture
def mock_file_upload_service():
    """Mock FileUploadService.

    Synchronous static methods (validate_upload, classify_file) are replaced
    with regular MagicMock so they don't return coroutines.
    """
    mock = AsyncMock(spec=FileUploadService)
    # These are @staticmethod in the real class; mock them synchronously
    mock.validate_upload = MagicMock(return_value=(True, None))
    mock.classify_file = MagicMock(return_value="text")
    return mock


@pytest.fixture
def mock_storage():
    """Mock file storage backend (BaseFileStorage)."""
    storage = MagicMock()
    storage.save = AsyncMock(return_value="user_id/abc123_test.txt")
    storage.load = AsyncMock(return_value=b"file content")
    storage.delete = AsyncMock()
    storage.get_full_path.return_value = None  # overridden per test
    return storage


@pytest.fixture
async def client_with_auth(
    mock_user,
    mock_redis,
    mock_db_session,
):
    """Async HTTP client with authenticated user override."""
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_redis] = lambda: mock_redis
    app.dependency_overrides[get_db_session] = lambda: mock_db_session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Auth-guard tests -- unauthenticated requests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_upload_requires_auth(client):
    """POST /files/upload without auth returns 401."""
    response = await client.post(f"{settings.API_V1_STR}/files/upload")
    assert response.status_code == 401


@pytest.mark.anyio
async def test_download_requires_auth(client):
    """GET /files/{id} without auth returns 401."""
    response = await client.get(f"{settings.API_V1_STR}/files/{uuid4()}")
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Upload file
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_upload_file(
    client_with_auth,
    mock_file_upload_service,
    mock_storage,
):
    """POST /files/upload uploads a file successfully."""
    app.dependency_overrides[get_file_upload_service] = lambda: mock_file_upload_service

    file_id = uuid4()
    # configure mocks for success
    mock_file_upload_service.create_chat_file = AsyncMock(
        return_value=MagicMock(
            id=file_id,
            filename="hello.txt",
            mime_type="text/plain",
            size=13,
            file_type="text",
        ),
    )
    mock_file_upload_service.parse_content = AsyncMock(return_value="Hello, world!")

    with patch(
        "app.api.routes.v1.files.get_file_storage",
        return_value=mock_storage,
    ):
        response = await client_with_auth.post(
            f"{settings.API_V1_STR}/files/upload",
            files={"file": ("hello.txt", b"Hello, world!", "text/plain")},
        )

    assert response.status_code == 201
    data = response.json()
    assert data["id"] == str(file_id)
    assert data["filename"] == "hello.txt"
    assert data["mime_type"] == "text/plain"
    assert data["size"] == 13
    assert data["file_type"] == "text"

    # Verify validation was called
    mock_file_upload_service.validate_upload.assert_called_once_with("text/plain", 13, "hello.txt")

    app.dependency_overrides.pop(get_file_upload_service, None)


def test_validate_upload_accepts_ofx_mime_and_extension():
    assert FileUploadService.validate_upload("application/ofx", 10, "extrato.ofx") == (True, None)
    assert FileUploadService.validate_upload("text/ofx", 10, "extrato.ofx") == (True, None)
    assert FileUploadService.validate_upload("application/x-ofx", 10, "extrato.ofx") == (True, None)
    assert FileUploadService.validate_upload("application/octet-stream", 10, "extrato.ofx") == (
        True,
        None,
    )
    assert FileUploadService.classify_file("application/octet-stream", "extrato.ofx") == "text"


@pytest.mark.anyio
async def test_upload_invalid_type(
    client_with_auth,
    mock_file_upload_service,
):
    """POST /files/upload with unsupported MIME type returns 400."""
    app.dependency_overrides[get_file_upload_service] = lambda: mock_file_upload_service

    mock_file_upload_service.validate_upload = MagicMock(
        return_value=(False, "File type 'application/x-shockwave-flash' is not supported."),
    )

    response = await client_with_auth.post(
        f"{settings.API_V1_STR}/files/upload",
        files={"file": ("test.swf", b"...payload...", "application/x-shockwave-flash")},
    )

    assert response.status_code == 400
    data = response.json()
    assert "not supported" in data["detail"]

    app.dependency_overrides.pop(get_file_upload_service, None)


# ---------------------------------------------------------------------------
# Download file
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_download_file(
    client_with_auth,
    mock_file_upload_service,
    mock_storage,
    tmp_path,
):
    """GET /files/{id} downloads a file."""
    app.dependency_overrides[get_file_upload_service] = lambda: mock_file_upload_service

    file_id = uuid4()
    file_content = b"Hello, file content!"

    # Create a real temp file so FileResponse can stream it
    file_dir = tmp_path / "user_id"
    file_dir.mkdir(parents=True, exist_ok=True)
    file_path = file_dir / "abc123_hello.txt"
    file_path.write_bytes(file_content)

    mock_file_upload_service.get_user_file = AsyncMock(
        return_value=MagicMock(
            id=file_id,
            filename="hello.txt",
            mime_type="text/plain",
            size=len(file_content),
            file_type="text",
            storage_path="user_id/abc123_hello.txt",
            user_id=uuid4(),
        ),
    )
    mock_storage.get_full_path.return_value = file_path

    with patch(
        "app.api.routes.v1.files.get_file_storage",
        return_value=mock_storage,
    ):
        response = await client_with_auth.get(
            f"{settings.API_V1_STR}/files/{file_id}"
        )

    assert response.status_code == 200
    assert "text/plain" in response.headers.get("content-type", "")
    assert response.content == file_content

    app.dependency_overrides.pop(get_file_upload_service, None)


@pytest.mark.anyio
async def test_download_file_not_found(
    client_with_auth,
    mock_file_upload_service,
):
    """GET /files/{id} with non-existent id returns 404."""
    app.dependency_overrides[get_file_upload_service] = lambda: mock_file_upload_service

    file_id = uuid4()
    mock_file_upload_service.get_user_file = AsyncMock(
        side_effect=NotFoundError(message="File not found"),
    )

    response = await client_with_auth.get(
        f"{settings.API_V1_STR}/files/{file_id}"
    )

    assert response.status_code == 404
    data = response.json()
    assert "File not found" in data["detail"]

    app.dependency_overrides.pop(get_file_upload_service, None)


# ---------------------------------------------------------------------------
# Get file info
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_get_file_info(
    client_with_auth,
    mock_file_upload_service,
    mock_user,
):
    """GET /files/{id}/info returns file metadata."""
    app.dependency_overrides[get_file_upload_service] = lambda: mock_file_upload_service

    file_id = uuid4()
    now = datetime.now(UTC)

    mock_file_upload_service.get_user_file = AsyncMock(
        return_value=MagicMock(
            id=file_id,
            filename="info.txt",
            mime_type="text/plain",
            size=42,
            file_type="text",
            user_id=mock_user.id,
            created_at=now,
        ),
    )

    response = await client_with_auth.get(
        f"{settings.API_V1_STR}/files/{file_id}/info"
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(file_id)
    assert data["filename"] == "info.txt"
    assert data["file_type"] == "text"
    assert data["size"] == 42
    assert data["user_id"] == str(mock_user.id)

    app.dependency_overrides.pop(get_file_upload_service, None)


@pytest.mark.anyio
async def test_list_files(
    client_with_auth,
    mock_file_upload_service,
):
    """GET /files lists latest user files."""
    app.dependency_overrides[get_file_upload_service] = lambda: mock_file_upload_service

    user_id = uuid4()
    file_id = uuid4()
    now = datetime.now(UTC)
    mock_file_upload_service.list_user_files = AsyncMock(
        return_value=[
            MagicMock(
                id=file_id,
                filename="extrato.docx",
                mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                size=1234,
                file_type="docx",
                created_at=now,
                user_id=user_id,
            )
        ]
    )

    response = await client_with_auth.get(f"{settings.API_V1_STR}/files")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == str(file_id)
    assert data[0]["filename"] == "extrato.docx"
    assert data[0]["file_type"] == "docx"

    app.dependency_overrides.pop(get_file_upload_service, None)
