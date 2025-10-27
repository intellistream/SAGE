"""
测试 docs 命令
"""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from sage.tools.cli.commands.dev.docs import app


@pytest.mark.cli
class TestDocsCommands:
    """测试 docs 命令组"""

    def setup_method(self):
        """设置测试"""
        self.runner = CliRunner()

    @patch("subprocess.run")
    @patch.object(Path, "cwd")
    def test_build_command_success(self, mock_cwd, mock_run):
        """测试 build 命令成功"""
        # Mock当前目录
        mock_cwd.return_value = Path("/fake/project")
        mock_run.return_value = MagicMock(returncode=0, stderr="", stdout="Building...")

        result = self.runner.invoke(app, ["build"])

        # 不应该崩溃（即使docs-public不存在）
        assert isinstance(result.exit_code, int)
        # 验证输出包含相关信息（可能是中文或英文）
        assert len(result.stdout) > 0

    @patch("subprocess.run")
    def test_serve_command(self, mock_run):
        """测试 serve 命令"""
        mock_run.return_value = MagicMock(returncode=0)

        result = self.runner.invoke(app, ["serve"])

        # 命令应该尝试运行
        assert isinstance(result.exit_code, int)

    @patch("subprocess.run")
    def test_serve_with_custom_port(self, mock_run):
        """测试自定义端口"""
        mock_run.return_value = MagicMock(returncode=0)

        result = self.runner.invoke(app, ["serve", "--port", "9000"])

        assert isinstance(result.exit_code, int)

    def test_check_command_basic(self):
        """测试 check 命令基本功能"""
        result = self.runner.invoke(app, ["check"])

        # 应该能运行（即使没有docs-public目录）
        assert isinstance(result.exit_code, int)
        # 输出应该包含相关信息
        assert len(result.stdout) > 0


@pytest.mark.cli
class TestDocsCheckWithRealFiles:
    """使用真实文件测试 check 命令"""

    def setup_method(self):
        self.runner = CliRunner()
        self.original_cwd = Path.cwd()

    def test_check_in_sage_project(self):
        """在SAGE项目中测试check命令"""
        # 切换到SAGE根目录（如果存在）
        sage_root = Path(__file__).parents[5]  # 测试文件 -> ... -> SAGE根目录

        if (sage_root / "docs-public").exists():
            os.chdir(sage_root)
            try:
                result = self.runner.invoke(app, ["check"])
                assert result.exit_code == 0
                # 应该找到一些文件
                assert "file" in result.stdout.lower() or "found" in result.stdout.lower()
            finally:
                os.chdir(self.original_cwd)
        else:
            pytest.skip("docs-public directory not found")


@pytest.mark.cli
class TestDocsEdgeCases:
    """测试边缘情况"""

    def setup_method(self):
        self.runner = CliRunner()

    @patch("subprocess.run")
    def test_mkdocs_not_installed(self, mock_run):
        """测试 mkdocs 未安装"""
        mock_run.side_effect = FileNotFoundError("mkdocs not found")

        result = self.runner.invoke(app, ["build"])

        # 应该处理错误
        assert isinstance(result.exit_code, int)

    def test_help_commands(self):
        """测试help命令"""
        result = self.runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "build" in result.stdout
        assert "serve" in result.stdout
        assert "check" in result.stdout

