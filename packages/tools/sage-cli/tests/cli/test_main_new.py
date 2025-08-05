#!/usr/bin/env python3
"""
Tests for sage.cli.main
完整测试CLI主入口点的所有功能
"""

import pytest
from typer.testing import CliRunner
from unittest.mock import patch, MagicMock

# Mock all the CLI sub-modules before importing main
with patch.dict('sys.modules', {
    'sage.cli.job': MagicMock(),
    'sage.cli.deploy': MagicMock(),
    'sage.cli.jobmanager_controller': MagicMock(),
    'sage.cli.worker_manager': MagicMock(),
    'sage.cli.head_manager': MagicMock(),
    'sage.cli.cluster_manager': MagicMock(),
    'sage.cli.extensions': MagicMock(),
    'sage.utils.system.network_utils': MagicMock(),
    'sage.jobmanager.jobmanager_client': MagicMock(),
}):
    from sage.cli.main import app


class TestMainCLI:
    """Test main CLI application"""
    
    def setup_method(self):
        """Setup test runner"""
        self.runner = CliRunner()
    
    @pytest.mark.unit
    def test_version_command(self):
        """测试版本命令输出正确的版本信息"""
        result = self.runner.invoke(app, ["version"])
        
        assert result.exit_code == 0
        assert "🚀 SAGE - Stream Analysis and Graph Engine" in result.stdout
        assert "Version: 0.1.2" in result.stdout
        assert "Author: IntelliStream" in result.stdout
        assert "Repository: https://github.com/intellistream/SAGE" in result.stdout
    
    @pytest.mark.unit
    @patch('sage.cli.main.get_config_manager')
    def test_config_command_success(self, mock_get_config_manager):
        """测试配置命令成功显示配置信息"""
        mock_config_manager = MagicMock()
        mock_config_manager.load_config.return_value = {
            'daemon': {'host': '127.0.0.1', 'port': 19001},
            'output': {'format': 'table', 'colors': True}
        }
        mock_get_config_manager.return_value = mock_config_manager
        
        result = self.runner.invoke(app, ["config"])
        
        assert result.exit_code == 0
        mock_config_manager.load_config.assert_called_once()
    
    @pytest.mark.unit
    @patch('sage.cli.main.get_config_manager')
    def test_config_command_error(self, mock_get_config_manager):
        """测试配置命令在配置加载失败时的错误处理"""
        mock_get_config_manager.side_effect = Exception("Config load error")
        
        result = self.runner.invoke(app, ["config"])
        
        assert result.exit_code == 0  # 应该优雅处理错误
    
    @pytest.mark.unit
    def test_main_help_display(self):
        """测试主帮助信息显示所有子命令"""
        result = self.runner.invoke(app, ["--help"])
        
        assert result.exit_code == 0
        assert "🚀 SAGE - Stream Analysis and Graph Engine CLI" in result.stdout
        assert "job" in result.stdout
        assert "deploy" in result.stdout
        assert "jobmanager" in result.stdout
        assert "cluster" in result.stdout
        assert "head" in result.stdout
        assert "worker" in result.stdout
        assert "extensions" in result.stdout
    
    @pytest.mark.unit
    def test_no_args_shows_help(self):
        """测试不带参数时显示帮助信息"""
        result = self.runner.invoke(app, [])
        
        assert result.exit_code == 0
        assert "Usage:" in result.stdout
    
    @pytest.mark.unit 
    def test_invalid_command(self):
        """测试无效命令的错误处理"""
        result = self.runner.invoke(app, ["invalid-command"])
        
        assert result.exit_code != 0
