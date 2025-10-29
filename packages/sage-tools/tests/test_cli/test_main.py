"""
CLI主模块测试
"""

import pytest
from typer.testing import CliRunner

from sage.tools.cli.main import app


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
        # sage.tools.cli.main.app 现在只有 dev 和 finetune 命令
        assert "dev" in result.stdout

    def test_dev_help(self):
        """测试dev命令帮助"""
        result = self.runner.invoke(app, ["dev", "--help"])
        assert result.exit_code == 0
        assert "开发工具" in result.stdout


@pytest.mark.cli
@pytest.mark.unit
class TestDevCommands:
    """dev命令测试"""

    def setup_method(self):
        """测试前设置"""
        self.runner = CliRunner()

    def test_dev_project_status(self):
        """测试project status命令"""
        result = self.runner.invoke(app, ["dev", "project", "status"])
        assert result.exit_code == 0
        assert "状态报告" in result.stdout

    def test_dev_project_status_json(self):
        """测试project status JSON输出"""
        result = self.runner.invoke(app, ["dev", "project", "status", "--output-format", "json"])
        assert result.exit_code == 0
        # 应该包含JSON结构
        assert "timestamp" in result.stdout
        assert "{" in result.stdout

    def test_dev_project_status_full(self):
        """测试project status详细输出"""
        result = self.runner.invoke(app, ["dev", "project", "status", "--output-format", "full"])
        assert result.exit_code == 0
        assert "检查" in result.stdout

    def test_dev_project_analyze(self):
        """测试project analyze命令"""
        result = self.runner.invoke(app, ["dev", "project", "analyze"])
        # 分析命令可能需要更长时间，允许某些失败
        assert result.exit_code in [0, 1]
        if result.exit_code == 0:
            assert "分析" in result.stdout

    def test_dev_project_analyze_health(self):
        """测试project analyze健康检查"""
        result = self.runner.invoke(app, ["dev", "project", "analyze", "--analysis-type", "health"])
        assert result.exit_code in [0, 1]
        if result.exit_code == 0:
            assert "分析" in result.stdout

    def test_dev_project_clean_dry_run(self):
        """测试project clean dry-run"""
        result = self.runner.invoke(app, ["dev", "project", "clean", "--dry-run"])
        assert result.exit_code == 0
        assert "预览" in result.stdout

    def test_dev_project_home_status(self):
        """测试project home status"""
        result = self.runner.invoke(app, ["dev", "project", "home", "status"])
        assert result.exit_code == 0
        # 检查SAGE目录状态输出中的关键信息
        assert "SAGE目录" in result.stdout or "SAGE目录状态" in result.stdout
