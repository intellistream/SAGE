"""
测试 DevNotesOrganizer
"""

import tempfile
from pathlib import Path

import pytest

from sage.tools.dev.maintenance import DevNotesOrganizer


@pytest.fixture
def temp_project():
    """创建临时项目结构"""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        devnotes = root / "docs" / "dev-notes"
        devnotes.mkdir(parents=True)

        # 创建测试文件
        (devnotes / "test1.md").write_text(
            """# Test 1

**Date**: 2024-01-01
**Author**: Test
**Summary**: Test summary

This is a test architecture document.
"""
        )

        (devnotes / "test2.md").write_text(
            """# Test 2

No metadata here.
This is about migration and refactoring.
"""
        )

        # 创建分类目录
        (devnotes / "architecture").mkdir()
        (devnotes / "architecture" / "design.md").write_text(
            """# Design Doc

**Date**: 2024-01-01
**Author**: Test
**Summary**: Design

Architecture design document.
"""
        )

        yield root


@pytest.mark.unit
class TestDevNotesOrganizer:
    """测试 DevNotesOrganizer 类"""

    def test_init(self, temp_project):
        """测试初始化"""
        organizer = DevNotesOrganizer(temp_project)
        assert organizer.root_dir == temp_project
        assert organizer.devnotes_dir == temp_project / "docs" / "dev-notes"

    def test_check_metadata(self, temp_project):
        """测试元数据检查"""
        organizer = DevNotesOrganizer(temp_project)

        # 有完整元数据的文件
        content1 = """# Test
**Date**: 2024-01-01
**Author**: Test
**Summary**: Summary
"""
        has_date, has_author, has_summary = organizer._check_metadata(content1)
        assert has_date
        assert has_author
        assert has_summary

        # 缺少元数据的文件
        content2 = """# Test
No metadata
"""
        has_date, has_author, has_summary = organizer._check_metadata(content2)
        assert not has_date
        assert not has_author
        assert not has_summary

    def test_suggest_category(self, temp_project):
        """测试分类建议"""
        organizer = DevNotesOrganizer(temp_project)

        # 架构相关
        assert (
            organizer._suggest_category(
                "ARCHITECTURE_DESIGN.md", "This is about system architecture and design"
            )
            == "architecture"
        )

        # 迁移相关
        assert (
            organizer._suggest_category("MIGRATION.md", "This is about migration and refactor")
            == "migration"
        )

        # 测试相关
        assert organizer._suggest_category("TEST_GUIDE.md", "Testing guide") == "testing"

    def test_analyze_file(self, temp_project):
        """测试文件分析"""
        organizer = DevNotesOrganizer(temp_project)

        # 分析有元数据的文件
        file1 = temp_project / "docs" / "dev-notes" / "test1.md"
        result1 = organizer.analyze_file(file1)

        assert result1["path"] == "test1.md"
        assert result1["has_date"]
        assert result1["has_author"]
        assert result1["has_summary"]
        assert result1["suggested_category"] == "architecture"
        assert result1["current_category"] == "root"
        assert not result1["is_empty"]

        # 分析缺少元数据的文件
        file2 = temp_project / "docs" / "dev-notes" / "test2.md"
        result2 = organizer.analyze_file(file2)

        assert result2["path"] == "test2.md"
        assert not result2["has_date"]
        assert not result2["has_author"]
        assert not result2["has_summary"]
        assert result2["suggested_category"] == "migration"

    def test_analyze_all(self, temp_project):
        """测试分析所有文件"""
        organizer = DevNotesOrganizer(temp_project)
        results = organizer.analyze_all()

        # 应该找到3个文件（test1.md, test2.md, architecture/design.md）
        assert len(results) == 3

        # 检查路径
        paths = {r["path"] for r in results}
        assert "test1.md" in paths
        assert "test2.md" in paths
        assert "architecture/design.md" in paths

    def test_generate_report(self, temp_project):
        """测试生成报告"""
        organizer = DevNotesOrganizer(temp_project)
        results = organizer.analyze_all()

        # 生成报告（不打印）
        report = organizer.generate_report(results, verbose=False)

        assert "total" in report
        assert "root_files" in report
        assert "missing_metadata" in report
        assert "empty_files" in report

        assert report["total"] == 3
        assert len(report["root_files"]) == 2  # test1.md, test2.md

    def test_empty_file_detection(self, temp_project):
        """测试空文件检测"""
        # 创建空文件
        empty_file = temp_project / "docs" / "dev-notes" / "empty.md"
        empty_file.write_text("# Empty\n")

        organizer = DevNotesOrganizer(temp_project)
        result = organizer.analyze_file(empty_file)

        assert result["is_empty"]  # 少于100字节


@pytest.mark.unit
class TestDevNotesOrganizerEdgeCases:
    """测试边缘情况"""

    def test_nonexistent_directory(self):
        """测试不存在的目录"""
        organizer = DevNotesOrganizer(Path("/nonexistent"))
        results = organizer.analyze_all()
        # 应该返回空列表而不是报错
        assert results == []

    def test_file_outside_devnotes(self, temp_project):
        """测试dev-notes目录外的文件"""
        organizer = DevNotesOrganizer(temp_project)
        outside_file = temp_project / "docs" / "other.md"
        outside_file.parent.mkdir(exist_ok=True)
        outside_file.write_text("# Other")

        result = organizer.analyze_file(outside_file)
        assert "error" in result

    def test_unicode_content(self, temp_project):
        """测试Unicode内容"""
        devnotes = temp_project / "docs" / "dev-notes"
        unicode_file = devnotes / "unicode.md"
        unicode_file.write_text(
            """# 中文标题

**Date**: 2024-01-01
**Author**: 测试作者
**Summary**: 这是一个包含中文的测试文档

内容包含各种Unicode字符：🎉 ✅ 📝
"""
        )

        organizer = DevNotesOrganizer(temp_project)
        result = organizer.analyze_file(unicode_file)

        assert result["has_date"]
        assert result["has_author"]
        assert result["has_summary"]
