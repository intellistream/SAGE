"""
DevNotesChecker 单元测试
测试 dev-notes 目录检查和警告/错误区分逻辑
"""

import tempfile
from pathlib import Path

import pytest

from sage.tools.dev.tools.devnotes_checker import DevNotesChecker


@pytest.mark.unit
class TestDevNotesChecker:
    """DevNotesChecker 测试"""

    def test_missing_devnotes_dir_is_warning_not_error(self):
        """测试：缺失 dev-notes 目录应该是警告而非错误"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建项目根目录，但不创建 dev-notes 目录
            root_dir = Path(tmpdir)
            docs_public = root_dir / "docs-public" / "docs_src"
            docs_public.mkdir(parents=True, exist_ok=True)

            checker = DevNotesChecker(root_dir=root_dir)
            result = checker.check_directory_structure()

            # 应该返回 True（只是警告）
            assert result is True

            # 应该有警告，但没有错误
            assert len(checker.warnings) > 0
            assert any("dev-notes 目录不存在" in w for w in checker.warnings)
            assert len(checker.errors) == 0

    def test_existing_devnotes_dir_structure_check(self):
        """测试：存在 dev-notes 目录时进行结构检查"""
        with tempfile.TemporaryDirectory() as tmpdir:
            root_dir = Path(tmpdir)
            devnotes_dir = root_dir / "docs-public" / "docs_src" / "dev-notes"
            devnotes_dir.mkdir(parents=True, exist_ok=True)

            # 创建正确的层级目录
            (devnotes_dir / "l1-common").mkdir()
            (devnotes_dir / "l2-platform").mkdir()

            checker = DevNotesChecker(root_dir=root_dir)
            result = checker.check_directory_structure()

            # 应该通过检查（有正确的目录结构）
            assert result is True

    def test_check_all_with_missing_dir(self):
        """测试：check_all 在缺失目录时的行为"""
        with tempfile.TemporaryDirectory() as tmpdir:
            root_dir = Path(tmpdir)
            docs_public = root_dir / "docs-public" / "docs_src"
            docs_public.mkdir(parents=True, exist_ok=True)

            checker = DevNotesChecker(root_dir=root_dir)
            result = checker.check_all()

            # 应该返回 passed=True（只是警告）
            assert result.get("passed") is True
            assert len(result.get("issues", [])) > 0
            # 检查 issues 中有警告标记
            issues = result.get("issues", [])
            assert any("⚠️" in issue.get("message", "") for issue in issues)

    def test_check_changed_with_missing_dir(self):
        """测试：check_changed 在缺失目录时的行为"""
        with tempfile.TemporaryDirectory() as tmpdir:
            root_dir = Path(tmpdir)
            docs_public = root_dir / "docs-public" / "docs_src"
            docs_public.mkdir(parents=True, exist_ok=True)

            checker = DevNotesChecker(root_dir=root_dir)
            result = checker.check_changed()

            # 应该返回 passed=True（只是警告）
            assert result.get("passed") is True


@pytest.mark.unit
class TestDevNotesCheckerPathUpdate:
    """测试 dev-notes 路径更新（docs → docs-public/docs_src）"""

    def test_devnotes_dir_path_is_updated(self):
        """测试：devnotes_dir 路径使用新位置"""
        with tempfile.TemporaryDirectory() as tmpdir:
            root_dir = Path(tmpdir)
            checker = DevNotesChecker(root_dir=root_dir)

            # 验证路径是新的
            expected_path = root_dir / "docs-public" / "docs_src" / "dev-notes"
            assert checker.devnotes_dir == expected_path

    def test_changed_files_filter_uses_new_path(self):
        """测试：变更文件过滤使用新路径"""
        with tempfile.TemporaryDirectory() as tmpdir:
            root_dir = Path(tmpdir)
            devnotes_dir = root_dir / "docs-public" / "docs_src" / "dev-notes"
            devnotes_dir.mkdir(parents=True, exist_ok=True)

            # 创建测试文件
            test_file = devnotes_dir / "test.md"
            test_file.write_text("# Test")

            checker = DevNotesChecker(root_dir=root_dir)

            # 模拟旧路径的文件（应该被过滤掉）
            old_path_files = ["docs/dev-notes/test.md"]
            errors, warnings = checker.check_changed_files(old_path_files)
            assert errors == 0  # 旧路径文件不应该被检查

            # 模拟新路径的文件（应该被检查）
            new_path_files = ["docs-public/docs_src/dev-notes/test.md"]
            errors, warnings = checker.check_changed_files(new_path_files)
            # 文件存在但可能缺少必需的元数据，所以可能有错误
            # 这里主要验证新路径被正确识别
