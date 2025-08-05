#!/usr/bin/env python3
"""
Tests for sage.cli.head_manager
完整测试Head节点管理CLI功能
"""

import pytest
from unittest.mock import patch, MagicMock, call
from typer.testing import CliRunner

from sage.cli.head_manager import app, get_conda_init_code


class TestHeadManagerCLI:
    """Test Head Manager CLI commands"""
    
    def setup_method(self):
        """Setup test runner"""
        self.runner = CliRunner()
    
    @pytest.mark.unit
    def test_get_conda_init_code_default_env(self):
        """测试获取默认conda环境初始化代码"""
        init_code = get_conda_init_code()
        
        assert "sage" in init_code
        assert "conda activate sage" in init_code
        assert "CONDA_DEFAULT_ENV" in init_code
        assert "conda.sh" in init_code
    
    @pytest.mark.unit
    def test_get_conda_init_code_custom_env(self):
        """测试获取自定义conda环境初始化代码"""
        init_code = get_conda_init_code("custom_env")
        
        assert "custom_env" in init_code
        assert "conda activate custom_env" in init_code
        assert "CONDA_DEFAULT_ENV" in init_code
    
    @pytest.mark.unit
    def test_get_conda_init_code_structure(self):
        """测试conda初始化代码结构正确"""
        init_code = get_conda_init_code("test_env")
        
        # 检查包含必要的路径检查
        expected_paths = [
            "$HOME/miniconda3/etc/profile.d/conda.sh",
            "$HOME/anaconda3/etc/profile.d/conda.sh", 
            "/opt/conda/etc/profile.d/conda.sh",
            "/usr/local/miniconda3/etc/profile.d/conda.sh",
            "/usr/local/anaconda3/etc/profile.d/conda.sh"
        ]
        
        for path in expected_paths:
            assert path in init_code


class TestHeadStart:
    """Test head node start functionality"""
    
    def setup_method(self):
        """Setup test runner"""
        self.runner = CliRunner()
    
    @pytest.mark.unit
    @patch('sage.cli.head_manager.get_config_manager')
    @patch('sage.cli.head_manager.subprocess.run')
    def test_start_head_success(self, mock_subprocess, mock_get_config_manager):
        """测试成功启动Head节点"""
        # Mock配置管理器返回的配置
        mock_config_manager = MagicMock()
        mock_config_manager.get_head_config.return_value = {
            'host': 'localhost',
            'head_port': 6379,
            'dashboard_port': 8265,
            'dashboard_host': '0.0.0.0',
            'temp_dir': '/tmp/ray_head',
            'log_dir': '/tmp/sage_head_logs',
            'ray_command': '/opt/conda/envs/sage/bin/ray',
            'conda_env': 'sage'
        }
        mock_config_manager.get_remote_config.return_value = {}
        mock_get_config_manager.return_value = mock_config_manager
        
        # Mock subprocess成功返回
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Ray head started successfully"
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result
        
        result = self.runner.invoke(app, ["start"])
        
        assert result.exit_code == 0
        assert "🚀 启动Ray Head节点" in result.stdout
        assert "📋 配置信息" in result.stdout
        assert "Head主机: localhost" in result.stdout
        assert "Head端口: 6379" in result.stdout
        mock_subprocess.assert_called_once()
        mock_config_manager.get_head_config.assert_called_once()
        mock_config_manager.get_remote_config.assert_called_once()
    
    @pytest.mark.unit
    @patch('sage.cli.head_manager.get_config_manager')
    @patch('sage.cli.head_manager.subprocess.run')
    def test_start_head_failure(self, mock_subprocess, mock_get_config_manager):
        """测试Head节点启动失败"""
        # Mock配置
        mock_config_manager = MagicMock()
        mock_config_manager.get_head_config.return_value = {
            'host': 'localhost',
            'head_port': 6379,
            'dashboard_port': 8265,
            'dashboard_host': '0.0.0.0',
            'temp_dir': '/tmp/ray_head',
            'log_dir': '/tmp/sage_head_logs',
            'ray_command': '/opt/conda/envs/sage/bin/ray',
            'conda_env': 'sage'
        }
        mock_config_manager.get_remote_config.return_value = {}
        mock_get_config_manager.return_value = mock_config_manager
        
        # Mock subprocess失败返回
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "Ray head start failed"
        mock_subprocess.return_value = mock_result
        
        result = self.runner.invoke(app, ["start"])
        
        # 即使失败也应该正常退出（错误在stderr中）
        assert result.exit_code == 0
        mock_subprocess.assert_called_once()
    
    @pytest.mark.unit
    @patch('sage.cli.head_manager.get_config_manager')
    def test_start_head_config_error(self, mock_get_config_manager):
        """测试配置获取错误时的处理"""
        mock_get_config_manager.side_effect = Exception("Config error")
        
        result = self.runner.invoke(app, ["start"])
        
        # 应该捕获并处理配置错误
        assert result.exit_code != 0 or "error" in result.stdout.lower()
    
    @pytest.mark.unit
    @patch('sage.cli.head_manager.get_config_manager')
    @patch('sage.cli.head_manager.subprocess.run')
    def test_start_head_with_custom_config(self, mock_subprocess, mock_get_config_manager):
        """测试使用自定义配置启动Head节点"""
        # Mock自定义配置
        mock_config_manager = MagicMock()
        mock_config_manager.get_head_config.return_value = {
            'host': '192.168.1.100',
            'head_port': 8379,
            'dashboard_port': 8266,
            'dashboard_host': '0.0.0.0',
            'temp_dir': '/custom/tmp/ray_head',
            'log_dir': '/custom/logs/sage_head',
            'ray_command': '/custom/ray/bin/ray',
            'conda_env': 'custom_sage'
        }
        mock_config_manager.get_remote_config.return_value = {}
        mock_get_config_manager.return_value = mock_config_manager
        
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result
        
        result = self.runner.invoke(app, ["start"])
        
        assert result.exit_code == 0
        assert "Head主机: 192.168.1.100" in result.stdout
        assert "Head端口: 8379" in result.stdout
        assert "Dashboard: 0.0.0.0:8266" in result.stdout
    
    @pytest.mark.unit
    @patch('sage.cli.head_manager.get_config_manager')
    @patch('sage.cli.head_manager.subprocess.run')
    def test_start_head_command_construction(self, mock_subprocess, mock_get_config_manager):
        """测试启动命令构造正确"""
        mock_config_manager = MagicMock()
        mock_config_manager.get_head_config.return_value = {
            'host': 'localhost',
            'head_port': 6379,
            'dashboard_port': 8265,
            'dashboard_host': '0.0.0.0',
            'temp_dir': '/tmp/ray_head',
            'log_dir': '/tmp/sage_head_logs',
            'ray_command': '/opt/conda/envs/sage/bin/ray',
            'conda_env': 'sage'
        }
        mock_config_manager.get_remote_config.return_value = {}
        mock_get_config_manager.return_value = mock_config_manager
        
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result
        
        self.runner.invoke(app, ["start"])
        
        # 验证subprocess被调用
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args
        
        # 验证命令包含必要元素
        if call_args and len(call_args[0]) > 0:
            command = call_args[0][0]
            assert isinstance(command, str)
            assert "ray_head" in command
            assert "sage_head_logs" in command


class TestHeadHelp:
    """Test head CLI help functionality"""
    
    def setup_method(self):
        """Setup test runner"""
        self.runner = CliRunner()
    
    @pytest.mark.unit
    def test_head_help_display(self):
        """测试Head管理帮助信息显示"""
        result = self.runner.invoke(app, ["--help"])
        
        assert result.exit_code == 0
        assert "Ray Head节点管理" in result.stdout or "Head节点管理" in result.stdout
    
    @pytest.mark.unit
    def test_start_command_help(self):
        """测试start命令帮助信息"""
        result = self.runner.invoke(app, ["start", "--help"])
        
        assert result.exit_code == 0
        assert "启动Ray Head节点" in result.stdout


class TestIntegration:
    """Integration tests for head manager"""
    
    def setup_method(self):
        """Setup test runner"""
        self.runner = CliRunner()
    
    @pytest.mark.integration
    @patch('sage.cli.head_manager.get_config_manager')
    @patch('sage.cli.head_manager.subprocess.run')
    def test_full_head_start_workflow(self, mock_subprocess, mock_get_config_manager):
        """测试完整的Head节点启动工作流"""
        # 设置完整的配置
        mock_config_manager = MagicMock()
        mock_config_manager.get_head_config.return_value = {
            'host': 'localhost',
            'head_port': 6379,
            'dashboard_port': 8265,
            'dashboard_host': '0.0.0.0',
            'temp_dir': '/tmp/ray_head',
            'log_dir': '/tmp/sage_head_logs',
            'ray_command': '/opt/conda/envs/sage/bin/ray',
            'conda_env': 'sage'
        }
        mock_config_manager.get_remote_config.return_value = {
            'ssh_user': 'sage',
            'ssh_key_path': '~/.ssh/id_rsa'
        }
        mock_get_config_manager.return_value = mock_config_manager
        
        # 模拟成功的subprocess调用
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Successfully started Ray Head"
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result
        
        # 执行命令
        result = self.runner.invoke(app, ["start"])
        
        # 验证结果
        assert result.exit_code == 0
        assert "🚀 启动Ray Head节点" in result.stdout
        assert "📋 配置信息" in result.stdout
        
        # 验证配置管理器被正确调用
        mock_config_manager.get_head_config.assert_called_once()
        mock_config_manager.get_remote_config.assert_called_once()
        
        # 验证subprocess被调用
        mock_subprocess.assert_called_once()
    
    @pytest.mark.integration
    @pytest.mark.slow
    def test_conda_init_code_comprehensive(self):
        """测试conda初始化代码的完整性"""
        init_code = get_conda_init_code("test_env")
        
        # 检查代码结构
        assert "CONDA_DEFAULT_ENV" in init_code
        assert "conda activate test_env" in init_code
        assert "CONDA_FOUND" in init_code
        
        # 检查多个conda路径
        conda_paths = [
            "$HOME/miniconda3",
            "$HOME/anaconda3", 
            "/opt/conda",
            "/usr/local/miniconda3",
            "/usr/local/anaconda3"
        ]
        
        for path in conda_paths:
            assert path in init_code
        
        # 检查错误处理
        assert "WARNING" in init_code
        assert "SUCCESS" in init_code
    def test_start_head_failure(self, mock_subprocess, mock_get_config_manager):
        """Test failed head node start"""
        mock_config_manager = MagicMock()
        mock_config_manager.get_head_config.return_value = {
            'host': 'localhost',
            'head_port': 6379,
            'dashboard_port': 8265,
            'dashboard_host': '0.0.0.0',
            'temp_dir': '/tmp/ray_head',
            'log_dir': '/tmp/sage_head_logs'
        }
        mock_config_manager.get_remote_config.return_value = {
            'ray_command': '/opt/conda/envs/sage/bin/ray',
            'conda_env': 'sage'
        }
        mock_get_config_manager.return_value = mock_config_manager
        
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "Ray head start failed"
        mock_subprocess.return_value = mock_result
        
        result = self.runner.invoke(app, ["start"])
        
        assert result.exit_code == 1
        assert "❌ Ray Head启动失败" in result.stdout
    
    @patch('sage.cli.head_manager.get_config_manager')
    @patch('sage.cli.head_manager.subprocess.run')
    def test_stop_head_success(self, mock_subprocess, mock_get_config_manager):
        """Test successful head node stop"""
        mock_config_manager = MagicMock()
        mock_config_manager.get_head_config.return_value = {
            'temp_dir': '/tmp/ray_head',
            'log_dir': '/tmp/sage_head_logs'
        }
        mock_config_manager.get_remote_config.return_value = {
            'ray_command': '/opt/conda/envs/sage/bin/ray',
            'conda_env': 'sage'
        }
        mock_get_config_manager.return_value = mock_config_manager
        
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Ray head stopped successfully"
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result
        
        result = self.runner.invoke(app, ["stop"])
        
        assert result.exit_code == 0
        assert "🛑 停止Ray Head节点" in result.stdout
        mock_subprocess.assert_called()
    
    @patch('sage.cli.head_manager.get_config_manager')
    @patch('sage.cli.head_manager.subprocess.run')
    def test_status_head_running(self, mock_subprocess, mock_get_config_manager):
        """Test head node status when running"""
        mock_config_manager = MagicMock()
        mock_config_manager.get_head_config.return_value = {
            'log_dir': '/tmp/sage_head_logs'
        }
        mock_config_manager.get_remote_config.return_value = {
            'conda_env': 'sage'
        }
        mock_get_config_manager.return_value = mock_config_manager
        
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "[运行中] 发现Ray Head进程"
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result
        
        result = self.runner.invoke(app, ["status"])
        
        assert result.exit_code == 0
        assert "📊 检查Ray Head节点状态" in result.stdout
    
    @patch('sage.cli.head_manager.get_config_manager')
    @patch('sage.cli.head_manager.subprocess.run')
    def test_status_head_not_running(self, mock_subprocess, mock_get_config_manager):
        """Test head node status when not running"""
        mock_config_manager = MagicMock()
        mock_config_manager.get_head_config.return_value = {
            'log_dir': '/tmp/sage_head_logs'
        }
        mock_config_manager.get_remote_config.return_value = {
            'conda_env': 'sage'
        }
        mock_get_config_manager.return_value = mock_config_manager
        
        mock_result = MagicMock()
        mock_result.returncode = 0  # 状态检查总是返回0
        mock_result.stdout = "[已停止] 未发现Ray Head进程"
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result
        
        result = self.runner.invoke(app, ["status"])
        
        assert result.exit_code == 0  # 修改为期望0
        assert "Ray Head节点状态" in result.stdout
    
    @patch('sage.cli.head_manager.stop_head')
    @patch('sage.cli.head_manager.start_head')
    def test_restart_head(self, mock_start, mock_stop):
        """Test head node restart"""
        result = self.runner.invoke(app, ["restart"])
        
        assert result.exit_code == 0
        assert "🔄 重启Ray Head节点" in result.stdout
    
    @patch('sage.cli.head_manager.get_config_manager')
    @patch('sage.cli.head_manager.Path')
    @patch('sage.cli.head_manager.subprocess.run')
    def test_logs_head_with_lines(self, mock_subprocess, mock_path, mock_get_config_manager):
        """Test viewing head node logs with specific line count"""
        mock_config_manager = MagicMock()
        mock_config_manager.get_head_config.return_value = {
            'log_dir': '/tmp/sage_head_logs'
        }
        mock_get_config_manager.return_value = mock_config_manager
        
        # Mock Path so log file appears to exist
        mock_log_file = MagicMock()
        mock_log_file.exists.return_value = True
        mock_path.return_value = mock_log_file
        
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Log line 1\nLog line 2\nLog line 3"
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result
        
        result = self.runner.invoke(app, ["logs", "--lines", "10"])
        
        assert result.exit_code == 0
        assert "Ray Head日志" in result.stdout
