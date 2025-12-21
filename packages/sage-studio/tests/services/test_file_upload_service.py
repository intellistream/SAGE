import shutil
from io import BytesIO

import pytest

from sage.studio.services.file_upload_service import FileUploadService


@pytest.fixture
def temp_upload_dir(tmp_path):
    upload_dir = tmp_path / "uploads"
    yield upload_dir
    if upload_dir.exists():
        shutil.rmtree(upload_dir)


@pytest.mark.asyncio
async def test_upload_file(temp_upload_dir):
    service = FileUploadService(upload_dir=temp_upload_dir)

    # Create a dummy file
    content = b"Hello, world!"
    file = BytesIO(content)
    filename = "test.txt"

    metadata = await service.upload_file(file, filename)

    assert metadata.original_name == filename
    assert metadata.size_bytes == len(content)
    assert metadata.file_type == ".txt"
    assert (temp_upload_dir / metadata.filename).exists()
    assert (temp_upload_dir / metadata.filename).read_bytes() == content


@pytest.mark.asyncio
async def test_list_files(temp_upload_dir):
    service = FileUploadService(upload_dir=temp_upload_dir)

    file1 = BytesIO(b"content1")
    await service.upload_file(file1, "file1.txt")

    file2 = BytesIO(b"content2")
    await service.upload_file(file2, "file2.md")

    files = service.list_files()
    assert len(files) == 2
    assert any(f.original_name == "file1.txt" for f in files)
    assert any(f.original_name == "file2.md" for f in files)


@pytest.mark.asyncio
async def test_delete_file(temp_upload_dir):
    service = FileUploadService(upload_dir=temp_upload_dir)

    file = BytesIO(b"content")
    metadata = await service.upload_file(file, "test.txt")

    assert service.delete_file(metadata.file_id)
    assert not (temp_upload_dir / metadata.filename).exists()
    assert service.get_file(metadata.file_id) is None


@pytest.mark.asyncio
async def test_invalid_file_type(temp_upload_dir):
    service = FileUploadService(upload_dir=temp_upload_dir)

    file = BytesIO(b"content")
    with pytest.raises(ValueError, match="不支持的文件类型"):
        await service.upload_file(file, "test.exe")


@pytest.mark.asyncio
async def test_file_too_large(temp_upload_dir):
    service = FileUploadService(upload_dir=temp_upload_dir)

    # 11MB file
    content = b"0" * (11 * 1024 * 1024)
    file = BytesIO(content)

    with pytest.raises(ValueError, match="文件过大"):
        await service.upload_file(file, "large.txt")
