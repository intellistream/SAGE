#!/usr/bin/env python3
"""
Tests for sage.cli.main
完整测试CLI主入口点的所有功能
"""

import pytest
import sys
import subprocess
from typer.testing import CliRunner
from unittest.mock import patch, MagicMock

# Mock all the CLI sub-modules before importing main
with patch.dict('sys.modules', {
    'sage.kernel.cli.job': MagicMock(),
    'sage.kernel.cli.deploy': MagicMock(),
    'sage.kernel.cli.jobmanager_controller': MagicMock(),
    'sage.kernel.cli.worker_manager': MagicMock(),
    'sage.kernel.cli.head_manager': MagicMock(),
    'sage.kernel.cli.cluster_manager': MagicMock(),
    'sage.kernel.cli.extensions': MagicMock(),
    'sage.kernel.utils.system.network_utils': MagicMock(),
    'sage.kernel.kernels.jobmanager.jobmanager_client': MagicMock(),
}):
    from sage.kernel.cli.main import app


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
    @patch('sage.kernel.cli.config_manager.get_config_manager')
    def test_config_command_success(self, mock_get_config_manager):
        """测试配置命令成功显示配置信息"""
        mock_config_manager = MagicMock()
        mock_config_manager.load_config.return_value = {
            'daemon': {'host': '127.0.0.1', 'port': 19001},
            'output': {'format': 'table', 'colors': True}
        }
        mock_config_manager.config_path = "/mock/path/config.yaml"
        mock_get_config_manager.return_value = mock_config_manager
        
        result = self.runner.invoke(app, ["config"])
        
        assert result.exit_code == 0
        mock_config_manager.load_config.assert_called_once()
    
    @pytest.mark.unit
    @patch('sage.kernel.cli.config_manager.get_config_manager')
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

import pytest
from typer.testing import CliRunner
from unittest.mock import patch, MagicMock

from sage.kernel.cli.main import app


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
    @patch('sage.kernel.cli.config_manager.get_config_manager')
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
    @patch('sage.kernel.cli.config_manager.get_config_manager')
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
        
        assert result.exit_code == 2  # Typer shows help and exits with code 2
        assert "Usage:" in result.stdout
    
    @pytest.mark.unit
    def test_job_subcommand_registered(self):
        """测试作业管理子命令已注册"""
        result = self.runner.invoke(app, ["job", "--help"])
        
        assert result.exit_code == 0
        assert "📋 作业管理" in result.stdout or "作业管理" in result.stdout
    
    @pytest.mark.unit
    def test_deploy_subcommand_registered(self):
        """测试系统部署子命令已注册"""
        result = self.runner.invoke(app, ["deploy", "--help"])
        
        assert result.exit_code == 0
        assert "🎯 系统部署" in result.stdout or "系统部署" in result.stdout
    
    @pytest.mark.unit
    def test_jobmanager_subcommand_registered(self):
        """测试JobManager管理子命令已注册"""
        result = self.runner.invoke(app, ["jobmanager", "--help"])
        
        assert result.exit_code == 0
        assert "🛠️ JobManager管理" in result.stdout or "JobManager管理" in result.stdout
    
    @pytest.mark.unit
    def test_cluster_subcommand_registered(self):
        """测试集群管理子命令已注册"""
        result = self.runner.invoke(app, ["cluster", "--help"])
        
        assert result.exit_code == 0
        assert "🏗️ 集群管理" in result.stdout or "集群管理" in result.stdout
    
    @pytest.mark.unit
    def test_head_subcommand_registered(self):
        """测试Head节点管理子命令已注册"""
        result = self.runner.invoke(app, ["head", "--help"])
        
        assert result.exit_code == 0
        assert "🏠 Head节点管理" in result.stdout or "Head节点管理" in result.stdout
    
    @pytest.mark.unit
    def test_worker_subcommand_registered(self):
        """测试Worker节点管理子命令已注册"""
        result = self.runner.invoke(app, ["worker", "--help"])
        
        assert result.exit_code == 0
        assert "👷 Worker节点管理" in result.stdout or "Worker节点管理" in result.stdout
    
    @pytest.mark.unit
    def test_extensions_subcommand_registered(self):
        """测试扩展管理子命令已注册"""
        result = self.runner.invoke(app, ["extensions", "--help"])
        
        assert result.exit_code == 0
        assert "🧩 扩展管理" in result.stdout or "扩展管理" in result.stdout
    
    @pytest.mark.unit
    def test_invalid_command(self):
        """测试无效命令的错误处理"""
        result = self.runner.invoke(app, ["invalid-command"])
        
        assert result.exit_code != 0

def test_worker_subcommand_help():
    """Test worker subcommand help."""
    runner = CliRunner()
    result = runner.invoke(app, ["worker", "--help"])
    assert result.exit_code == 0
    assert "Worker节点管理" in result.stdout

@patch('tempfile.NamedTemporaryFile')
@patch('os.path.expanduser')
@patch('sage.kernel.cli.config_manager.ConfigManager.load_config')
def test_config_with_existing_config(mock_load_config, mock_expanduser, mock_tempfile):
    """Test config command with existing configuration."""
    # Mock the config
    mock_config = {
        'head': {'host': 'test-host', 'port': 6379},
        'workers_ssh_hosts': 'worker1:22,worker2:22'
    }
    mock_load_config.return_value = mock_config
    
    # Run the config command
    runner = CliRunner()
    result = runner.invoke(app, ["config"])
    assert result.exit_code == 0
    assert "SAGE 配置信息" in result.stdout

def test_main_script_execution():
    """Test running the CLI as a script."""
    result = subprocess.run(
        [sys.executable, "-m", "sage.kernel.cli.main", "--help"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    assert "Usage:" in result.stdout
    assert "SAGE" in result.stdout
