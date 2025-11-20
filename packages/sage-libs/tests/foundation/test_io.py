"""
Tests for foundation/io module

Tests cover:
- FileSource: File reading with mocking
- Basic source function behavior
"""

import tempfile
from pathlib import Path

import pytest


@pytest.mark.unit
class TestFileSource:
    """Test FileSource"""

    def test_init_with_config(self):
        """测试使用配置初始化"""
        from sage.libs.foundation.io.source import FileSource

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("test line")
            filepath = f.name

        try:
            config = {"data_path": filepath}
            source = FileSource(config=config)

            assert source.config == config
            assert source.data_path == Path(filepath)
            assert source.file_pos == 0
            assert source.loop_reading is False
        finally:
            Path(filepath).unlink()

    def test_init_without_config_raises_error(self):
        """测试没有配置会报错"""
        from sage.libs.foundation.io.source import FileSource

        with pytest.raises(ValueError, match="config parameter is required"):
            FileSource()

    def test_resolve_absolute_path(self):
        """测试解析绝对路径"""
        from sage.libs.foundation.io.source import FileSource

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            filepath = f.name

        try:
            config = {"data_path": filepath}
            source = FileSource(config=config)

            resolved = source.resolve_data_path(filepath)
            assert resolved == Path(filepath)
            assert resolved.is_absolute()
        finally:
            Path(filepath).unlink()

    def test_execute_reads_line(self):
        """测试读取文件行"""
        from sage.libs.foundation.io.source import FileSource

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("line1\nline2\nline3")
            filepath = f.name

        try:
            config = {"data_path": filepath}
            source = FileSource(config=config)

            # Read first line
            line = source.execute()
            assert line == "line1"

            # Read second line
            line = source.execute()
            assert line == "line2"

            # Read third line
            line = source.execute()
            assert line == "line3"
        finally:
            Path(filepath).unlink()

    def test_execute_with_loop_reading(self):
        """测试循环读取"""
        from sage.libs.foundation.io.source import FileSource

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("line1\nline2")
            filepath = f.name

        try:
            config = {"data_path": filepath, "loop_reading": True}
            source = FileSource(config=config)

            # Read first line
            line = source.execute()
            assert line == "line1"

            # Read second line
            line = source.execute()
            assert line == "line2"

            # Should loop back to first line
            line = source.execute()
            assert line == "line1"
        finally:
            Path(filepath).unlink()

    def test_execute_file_not_found(self):
        """测试文件不存在"""
        from sage.libs.foundation.io.source import FileSource

        config = {"data_path": "/nonexistent/file.txt"}
        source = FileSource(config=config)

        result = source.execute()
        assert result is None


@pytest.mark.unit
class TestHFDatasetBatch:
    """Test HFDatasetBatch"""

    def test_import(self):
        """测试能够导入HFDatasetBatch"""
        from sage.libs.foundation.io.batch import HFDatasetBatch

        assert HFDatasetBatch is not None
        assert hasattr(HFDatasetBatch, "__init__")

    def test_init_requires_config(self):
        """测试初始化需要配置"""
        from sage.libs.foundation.io.batch import HFDatasetBatch

        with pytest.raises(ValueError, match="config is required"):
            HFDatasetBatch()
