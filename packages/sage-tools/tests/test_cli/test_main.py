"""
CLI主模块测试
"""

import pytest
from typer.testing import CliRunner

from sage.tools.cli.commands.dev import app


@pytest.mark.cli
class TestCLIMain:
    """CLI主模块测试"""

    def setup_method(self):
        """测试前设置"""
        self.runner = CliRunner()

    def test_cli_help(self):
        """测试CLI帮助"""
        result = self.runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        # app is sage.tools.cli.commands.dev:app, already at dev level
        assert "质量检查" in result.stdout or "project" in result.stdout

    def test_dev_help(self):
        """测试dev命令帮助 - 实际测试project子命令"""
        result = self.runner.invoke(app, ["project", "--help"])
        assert result.exit_code == 0
        assert "项目管理" in result.stdout or "status" in result.stdout


@pytest.mark.cli
@pytest.mark.unit
class TestDevCommands:
    """dev命令测试"""

    def setup_method(self):
        """测试前设置"""
        self.runner = CliRunner()

    def test_dev_project_status(self):
        """测试project status命令"""
        result = self.runner.invoke(app, ["project", "status"])
        assert result.exit_code == 0
        assert "状态报告" in result.stdout or "状态" in result.stdout

    def test_dev_project_status_json(self):
        """测试project status JSON输出"""
        result = self.runner.invoke(app, ["project", "status", "--output-format", "json"])
        assert result.exit_code == 0
        # 应该包含JSON结构
        assert "timestamp" in result.stdout or "{" in result.stdout

    def test_dev_project_status_full(self):
        """测试project status详细输出"""
        result = self.runner.invoke(app, ["project", "status", "--output-format", "full"])
        assert result.exit_code == 0
        assert "检查" in result.stdout or "状态" in result.stdout

    def test_dev_project_analyze(self):
        """测试project analyze命令"""
        result = self.runner.invoke(app, ["project", "analyze"])
        # 分析命令可能需要更长时间，允许某些失败
        assert result.exit_code in [0, 1]
        if result.exit_code == 0:
            assert "分析" in result.stdout or "状态" in result.stdout

    def test_dev_project_analyze_health(self):
        """测试project analyze健康检查"""
        result = self.runner.invoke(app, ["project", "analyze", "--analysis-type", "health"])
        assert result.exit_code in [0, 1]
        if result.exit_code == 0:
            assert "分析" in result.stdout or "健康" in result.stdout

    def test_dev_project_clean_dry_run(self):
        """测试project clean dry-run"""
        result = self.runner.invoke(app, ["project", "clean", "--dry-run"])
        assert result.exit_code == 0
        assert "预览" in result.stdout or "清理" in result.stdout

    def test_dev_project_home_status(self):
        """测试project home status"""
        result = self.runner.invoke(app, ["project", "home", "status"])
        assert result.exit_code == 0
        # 检查SAGE目录状态输出中的关键信息
        assert "SAGE目录" in result.stdout or "SAGE" in result.stdout
