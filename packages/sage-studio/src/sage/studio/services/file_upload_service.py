from __future__ import annotations

import json
import logging
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import BinaryIO

from sage.common.config.user_paths import get_user_paths

logger = logging.getLogger(__name__)

# 允许的文件类型
ALLOWED_EXTENSIONS = {".pdf", ".md", ".txt", ".py", ".json", ".yaml", ".yml"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


@dataclass
class FileMetadata:
    """文件元数据"""

    file_id: str
    filename: str
    original_name: str
    file_type: str
    size_bytes: int
    upload_time: str  # ISO format
    path: str
    indexed: bool = False


class FileUploadService:
    """文件上传服务"""

    def __init__(self, upload_dir: str | Path | None = None):
        if upload_dir is None:
            upload_dir = get_user_paths().data_dir / "studio" / "uploads"

        self.upload_dir = Path(upload_dir).expanduser()
        self.upload_dir.mkdir(parents=True, exist_ok=True)

        self.metadata_file = self.upload_dir / "metadata.json"
        self._metadata: dict[str, FileMetadata] = {}
        self._load_metadata()

    def _load_metadata(self) -> None:
        """加载元数据"""
        if self.metadata_file.exists():
            with open(self.metadata_file) as f:
                data = json.load(f)
                self._metadata = {k: FileMetadata(**v) for k, v in data.items()}

    def _save_metadata(self) -> None:
        """保存元数据"""
        with open(self.metadata_file, "w") as f:
            data = {k: asdict(v) for k, v in self._metadata.items()}
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _validate_file(self, filename: str, size: int) -> None:
        """验证文件"""
        ext = Path(filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise ValueError(f"不支持的文件类型: {ext}")

        if size > MAX_FILE_SIZE:
            raise ValueError(
                f"文件过大: {size / 1024 / 1024:.1f}MB > {MAX_FILE_SIZE / 1024 / 1024}MB"
            )

    def _sanitize_filename(self, filename: str) -> str:
        """消毒文件名"""
        # 只保留文件名部分，去除路径
        name = Path(filename).name
        # 去除危险字符
        return "".join(c for c in name if c.isalnum() or c in "._-")

    async def upload_file(
        self,
        file: BinaryIO,
        filename: str,
    ) -> FileMetadata:
        """上传文件"""
        # 读取内容
        content = file.read()
        size = len(content)

        # 验证
        self._validate_file(filename, size)

        # 生成唯一 ID 和文件名
        file_id = str(uuid.uuid4())[:8]
        safe_name = self._sanitize_filename(filename)
        ext = Path(filename).suffix.lower()
        stored_name = f"{file_id}_{safe_name}"

        # 保存文件
        file_path = self.upload_dir / stored_name
        with open(file_path, "wb") as f:
            f.write(content)

        # 创建元数据
        metadata = FileMetadata(
            file_id=file_id,
            filename=stored_name,
            original_name=filename,
            file_type=ext,
            size_bytes=size,
            upload_time=datetime.now().isoformat(),
            path=str(file_path),
            indexed=False,
        )

        # 保存元数据
        self._metadata[file_id] = metadata
        self._save_metadata()

        logger.info(f"File uploaded: {filename} -> {stored_name}")
        return metadata

    def list_files(self) -> list[FileMetadata]:
        """列出所有文件"""
        return list(self._metadata.values())

    def get_file(self, file_id: str) -> FileMetadata | None:
        """获取文件元数据"""
        return self._metadata.get(file_id)

    def delete_file(self, file_id: str) -> bool:
        """删除文件"""
        metadata = self._metadata.get(file_id)
        if not metadata:
            return False

        # 删除文件
        file_path = Path(metadata.path)
        if file_path.exists():
            file_path.unlink()

        # 删除元数据
        del self._metadata[file_id]
        self._save_metadata()

        logger.info(f"File deleted: {file_id}")
        return True

    def get_file_path(self, file_id: str) -> Path | None:
        """获取文件路径"""
        metadata = self._metadata.get(file_id)
        if metadata:
            return Path(metadata.path)
        return None

    def mark_indexed(self, file_id: str) -> None:
        """标记文件已索引"""
        if file_id in self._metadata:
            self._metadata[file_id].indexed = True
            self._save_metadata()


# 单例
_service: FileUploadService | None = None


def get_file_upload_service() -> FileUploadService:
    global _service
    if _service is None:
        _service = FileUploadService()
    return _service
