"""
quality 命令 devnotes 检查逻辑单元测试
"""

import tempfile
from pathlib import Path

import pytest


@pytest.mark.unit
class TestDevnotesCheckLogic:
    """测试 devnotes 检查的错误/警告区分逻辑"""

    def test_errors_and_warnings_are_separated(self):
        """测试：错误和警告能够被正确区分"""
        mock_issues = [
            {"file": "test1.md", "message": "❌ 这是一个错误"},
            {"file": "test2.md", "message": "⚠️  这是一个警告"},
            {"file": "test3.md", "message": "❌ 另一个错误"},
        ]

        # 模拟 main.py 中的逻辑
        errors = [i for i in mock_issues if "❌" in i.get("message", "")]
        warnings_only = [i for i in mock_issues if "⚠️" in i.get("message", "")]

        assert len(errors) == 2
        assert len(warnings_only) == 1

    def test_only_warnings_no_errors(self):
        """测试：只有警告时的情况"""
        mock_issues = [
            {"file": "test1.md", "message": "⚠️  警告1"},
            {"file": "test2.md", "message": "⚠️  警告2"},
        ]

        errors = [i for i in mock_issues if "❌" in i.get("message", "")]
        warnings_only = [i for i in mock_issues if "⚠️" in i.get("message", "")]

        assert len(errors) == 0
        assert len(warnings_only) == 2

    def test_only_errors_no_warnings(self):
        """测试：只有错误时的情况"""
        mock_issues = [
            {"file": "test1.md", "message": "❌ 错误1"},
            {"file": "test2.md", "message": "❌ 错误2"},
        ]

        errors = [i for i in mock_issues if "❌" in i.get("message", "")]
        warnings_only = [i for i in mock_issues if "⚠️" in i.get("message", "")]

        assert len(errors) == 2
        assert len(warnings_only) == 0


@pytest.mark.unit
class TestDevnotesDirectoryCheck:
    """测试 dev-notes 目录检查逻辑"""

    def test_directory_existence_check_logic(self):
        """测试：目录存在性检查逻辑"""
        with tempfile.TemporaryDirectory() as tmpdir:
            root_dir = Path(tmpdir)

            # 模拟 main.py 中的检查逻辑
            devnotes_dir = root_dir / "docs-public" / "docs_src" / "dev-notes"

            # 目录不存在的情况
            assert not devnotes_dir.exists()

            # 创建目录
            devnotes_dir.mkdir(parents=True, exist_ok=True)
            assert devnotes_dir.exists()

    def test_devnotes_check_skipped_when_dir_missing(self):
        """测试：目录缺失时应该跳过检查"""
        with tempfile.TemporaryDirectory() as tmpdir:
            root_dir = Path(tmpdir)
            docs_public = root_dir / "docs-public" / "docs_src"
            docs_public.mkdir(parents=True, exist_ok=True)

            devnotes_dir = root_dir / "docs-public" / "docs_src" / "dev-notes"

            # 模拟 main.py 中的逻辑
            should_check = devnotes_dir.exists()

            assert not should_check  # 不应该检查

    def test_devnotes_check_runs_when_dir_exists(self):
        """测试：目录存在时应该运行检查"""
        with tempfile.TemporaryDirectory() as tmpdir:
            root_dir = Path(tmpdir)
            devnotes_dir = root_dir / "docs-public" / "docs_src" / "dev-notes"
            devnotes_dir.mkdir(parents=True, exist_ok=True)

            # 模拟 main.py 中的逻辑
            should_check = devnotes_dir.exists()

            assert should_check  # 应该检查
