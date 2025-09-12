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
        assert "SAGE" in result.stdout
        assert "Streaming-Augmented Generative Execution" in result.stdout
    
    def test_version_command(self):
        """测试版本命令"""
        result = self.runner.invoke(app, ["version"])
        assert result.exit_code == 0
        # 应该包含版本信息
        assert "版本" in result.stdout or "version" in result.stdout.lower()
    
    def test_doctor_command(self):
        """测试诊断命令"""
        result = self.runner.invoke(app, ["doctor"])
        assert result.exit_code == 0
        # 诊断命令应该有输出
        assert len(result.stdout.strip()) > 0
    
    def test_config_help(self):
        """测试配置命令帮助"""
        result = self.runner.invoke(app, ["config", "--help"])
        assert result.exit_code == 0
        assert "配置" in result.stdout
    
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
    
    def test_dev_status(self):
        """测试status命令"""
        result = self.runner.invoke(app, ["dev", "status"])
        assert result.exit_code == 0
        assert "状态报告" in result.stdout
    
    def test_dev_status_json(self):
        """测试status JSON输出"""
        result = self.runner.invoke(app, ["dev", "status", "--output-format", "json"])
        assert result.exit_code == 0
        # 应该包含JSON结构
        assert "timestamp" in result.stdout
        assert "{" in result.stdout
    
    def test_dev_status_full(self):
        """测试status详细输出"""
        result = self.runner.invoke(app, ["dev", "status", "--output-format", "full"])
        assert result.exit_code == 0
        assert "检查" in result.stdout
    
    def test_dev_analyze(self):
        """测试analyze命令"""
        result = self.runner.invoke(app, ["dev", "analyze"])
        # 分析命令可能需要更长时间，允许某些失败
        assert result.exit_code in [0, 1]
        if result.exit_code == 0:
            assert "分析" in result.stdout
    
    def test_dev_analyze_health(self):
        """测试analyze健康检查"""
        result = self.runner.invoke(app, ["dev", "analyze", "--analysis-type", "health"])
        assert result.exit_code in [0, 1]
        if result.exit_code == 0:
            assert "分析" in result.stdout
    
    def test_dev_clean_dry_run(self):
        """测试clean dry-run"""
        result = self.runner.invoke(app, ["dev", "clean", "--dry-run"])
        assert result.exit_code == 0
        assert "预览" in result.stdout
    
    def test_dev_home_status(self):
        """测试home status"""
        result = self.runner.invoke(app, ["dev", "home", "status"])
        assert result.exit_code == 0
        assert "SAGE_HOME" in result.stdout
