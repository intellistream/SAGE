"""
Tests for sage.cli.head_manager
"""
import pytest
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner

from sage.cli.head_manager import app


class TestHeadManager:
    """Test Head Manager CLI commands"""
    
    def setup_method(self):
        """Setup test runner"""
        self.runner = CliRunner()
    
    @patch('sage.cli.head_manager.get_config_manager')
    @patch('sage.cli.head_manager.subprocess.run')
    def test_start_head_success(self, mock_subprocess, mock_get_config_manager):
        """Test successful head node start"""
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
        mock_result.returncode = 0
        mock_result.stdout = "Ray head started successfully"
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result
        
        result = self.runner.invoke(app, ["start"])
        
        assert result.exit_code == 0
        assert "🚀 启动Ray Head节点" in result.stdout
        mock_subprocess.assert_called()
    
    @patch('sage.cli.head_manager.get_config_manager')
    @patch('sage.cli.head_manager.subprocess.run')
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
