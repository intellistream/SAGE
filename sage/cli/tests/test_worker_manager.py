"""
Tests for sage.cli.worker_manager
"""
import pytest
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner

from sage.cli.worker_manager import app, execute_remote_command


class TestWorkerManager:
    """Test Worker Manager CLI commands"""
    
    def setup_method(self):
        """Setup test runner"""
        self.runner = CliRunner()
    
    @patch('sage.cli.worker_manager.subprocess.run')
    @patch('sage.cli.worker_manager.get_config_manager')
    def test_execute_remote_command_success(self, mock_get_config_manager, mock_subprocess):
        """Test successful remote command execution"""
        mock_config_manager = MagicMock()
        mock_config_manager.get_ssh_config.return_value = {
            'user': 'testuser',
            'key_path': '~/.ssh/id_rsa',
            'connect_timeout': 10
        }
        mock_get_config_manager.return_value = mock_config_manager
        
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Command executed successfully"
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result
        
        result = execute_remote_command('testhost', 22, 'echo "test"')
        
        assert result is True
        mock_subprocess.assert_called_once()
    
    @patch('sage.cli.worker_manager.execute_remote_command')
    @patch('sage.cli.worker_manager.get_config_manager')
    def test_start_workers_success(self, mock_get_config_manager, mock_execute_remote):
        """Test successful worker nodes start"""
        mock_config_manager = MagicMock()
        mock_config_manager.get_head_config.return_value = {
            'host': 'head-node',
            'head_port': 6379
        }
        mock_config_manager.get_worker_config.return_value = {
            'bind_host': 'localhost',
            'temp_dir': '/tmp/ray_worker',
            'log_dir': '/tmp/sage_worker_logs'
        }
        mock_config_manager.get_remote_config.return_value = {
            'ray_command': '/opt/conda/envs/sage/bin/ray',
            'conda_env': 'sage'
        }
        mock_config_manager.get_workers_ssh_hosts.return_value = [
            ('worker1', 22),
            ('worker2', 22)
        ]
        mock_get_config_manager.return_value = mock_config_manager
        
        mock_execute_remote.return_value = True
        
        result = self.runner.invoke(app, ["start"])
        
        assert result.exit_code == 0
        assert "🚀 启动Ray Worker节点" in result.stdout
        assert "✅ 所有Worker节点启动成功" in result.stdout
        assert mock_execute_remote.call_count == 2  # Two workers
    
    @patch('sage.cli.worker_manager.execute_remote_command')
    @patch('sage.cli.worker_manager.get_config_manager')
    def test_start_workers_partial_failure(self, mock_get_config_manager, mock_execute_remote):
        """Test worker nodes start with partial failure"""
        mock_config_manager = MagicMock()
        mock_config_manager.get_head_config.return_value = {
            'host': 'head-node',
            'head_port': 6379
        }
        mock_config_manager.get_worker_config.return_value = {
            'bind_host': 'localhost',
            'temp_dir': '/tmp/ray_worker',
            'log_dir': '/tmp/sage_worker_logs'
        }
        mock_config_manager.get_remote_config.return_value = {
            'ray_command': '/opt/conda/envs/sage/bin/ray',
            'conda_env': 'sage'
        }
        mock_config_manager.get_workers_ssh_hosts.return_value = [
            ('worker1', 22),
            ('worker2', 22)
        ]
        mock_get_config_manager.return_value = mock_config_manager
        
        mock_execute_remote.side_effect = [True, False]  # Second worker fails
        
        result = self.runner.invoke(app, ["start"])
        
        assert result.exit_code == 1
        assert "⚠️  部分Worker节点启动失败" in result.stdout
    
    @patch('sage.cli.worker_manager.get_config_manager')
    def test_start_workers_no_workers_configured(self, mock_get_config_manager):
        """Test starting workers when none are configured"""
        mock_config_manager = MagicMock()
        mock_config_manager.get_workers_ssh_hosts.return_value = []
        mock_get_config_manager.return_value = mock_config_manager
        
        result = self.runner.invoke(app, ["start"])
        
        assert result.exit_code == 1
        assert "❌ 未配置任何worker节点" in result.stdout
    
    @patch('sage.cli.worker_manager.execute_remote_command')
    @patch('sage.cli.worker_manager.get_config_manager')
    def test_stop_workers_success(self, mock_get_config_manager, mock_execute_remote):
        """Test successful worker nodes stop"""
        mock_config_manager = MagicMock()
        mock_config_manager.get_worker_config.return_value = {
            'temp_dir': '/tmp/ray_worker',
            'log_dir': '/tmp/sage_worker_logs'
        }
        mock_config_manager.get_remote_config.return_value = {
            'ray_command': '/opt/conda/envs/sage/bin/ray',
            'conda_env': 'sage'
        }
        mock_config_manager.get_workers_ssh_hosts.return_value = [
            ('worker1', 22),
            ('worker2', 22)
        ]
        mock_get_config_manager.return_value = mock_config_manager
        
        mock_execute_remote.return_value = True
        
        result = self.runner.invoke(app, ["stop"])
        
        assert result.exit_code == 0
        assert "🛑 停止Ray Worker节点" in result.stdout
        assert "✅ 所有Worker节点停止操作完成" in result.stdout
    
    @patch('sage.cli.worker_manager.execute_remote_command')
    @patch('sage.cli.worker_manager.get_config_manager')
    def test_status_workers_all_running(self, mock_get_config_manager, mock_execute_remote):
        """Test worker status when all are running"""
        mock_config_manager = MagicMock()
        mock_config_manager.get_head_config.return_value = {
            'host': 'head-node',
            'head_port': 6379
        }
        mock_config_manager.get_worker_config.return_value = {
            'log_dir': '/tmp/sage_worker_logs'
        }
        mock_config_manager.get_remote_config.return_value = {
            'ray_command': '/opt/conda/envs/sage/bin/ray',
            'conda_env': 'sage'
        }
        mock_config_manager.get_workers_ssh_hosts.return_value = [
            ('worker1', 22),
            ('worker2', 22)
        ]
        mock_get_config_manager.return_value = mock_config_manager
        
        mock_execute_remote.return_value = True
        
        result = self.runner.invoke(app, ["status"])
        
        assert result.exit_code == 0
        assert "📊 检查Ray Worker节点状态" in result.stdout
        assert "✅ 所有Worker节点都在正常运行" in result.stdout
    
    @patch('sage.cli.worker_manager.execute_remote_command')
    @patch('sage.cli.worker_manager.get_config_manager')
    def test_status_workers_none_running(self, mock_get_config_manager, mock_execute_remote):
        """Test worker status when none are running"""
        mock_config_manager = MagicMock()
        mock_config_manager.get_head_config.return_value = {
            'host': 'head-node',
            'head_port': 6379
        }
        mock_config_manager.get_worker_config.return_value = {
            'log_dir': '/tmp/sage_worker_logs'
        }
        mock_config_manager.get_remote_config.return_value = {
            'ray_command': '/opt/conda/envs/sage/bin/ray',
            'conda_env': 'sage'
        }
        mock_config_manager.get_workers_ssh_hosts.return_value = [
            ('worker1', 22),
            ('worker2', 22)
        ]
        mock_get_config_manager.return_value = mock_config_manager
        
        mock_execute_remote.return_value = False
        
        result = self.runner.invoke(app, ["status"])
        
        assert result.exit_code == 0
        assert "❌ 没有Worker节点在运行" in result.stdout
    
    @patch('sage.cli.worker_manager.start_workers')
    @patch('sage.cli.worker_manager.stop_workers')
    def test_restart_workers(self, mock_stop, mock_start):
        """Test worker nodes restart"""
        result = self.runner.invoke(app, ["restart"])
        
        assert result.exit_code == 0
        assert "🔄 重启Ray Worker节点" in result.stdout
    
    @patch('sage.cli.worker_manager.get_config_manager')
    def test_show_config(self, mock_get_config_manager):
        """Test showing worker configuration"""
        mock_config_manager = MagicMock()
        mock_config_manager.get_head_config.return_value = {
            'host': 'head-node',
            'head_port': 6379,
            'dashboard_port': 8265,
            'dashboard_host': '0.0.0.0'
        }
        mock_config_manager.get_worker_config.return_value = {
            'bind_host': 'localhost',
            'temp_dir': '/tmp/ray_worker',
            'log_dir': '/tmp/sage_worker_logs'
        }
        mock_config_manager.get_ssh_config.return_value = {
            'user': 'sage',
            'key_path': '~/.ssh/id_rsa'
        }
        mock_config_manager.get_remote_config.return_value = {
            'sage_home': '/home/sage',
            'python_path': '/opt/conda/envs/sage/bin/python',
            'ray_command': '/opt/conda/envs/sage/bin/ray'
        }
        mock_config_manager.get_workers_ssh_hosts.return_value = [
            ('worker1', 22),
            ('worker2', 8022)
        ]
        mock_get_config_manager.return_value = mock_config_manager
        
        result = self.runner.invoke(app, ["config"])
        
        assert result.exit_code == 0
        assert "📋 当前Worker配置信息" in result.stdout
        assert "head-node" in result.stdout
        assert "Worker节点数量: 2" in result.stdout
    
    @patch('sage.cli.worker_manager.DeploymentManager')
    @patch('sage.cli.worker_manager.get_config_manager')
    def test_deploy_workers_success(self, mock_get_config_manager, mock_deployment_manager):
        """Test successful worker deployment"""
        mock_deployment_instance = MagicMock()
        mock_deployment_instance.deploy_to_all_workers.return_value = (2, 2)
        mock_deployment_manager.return_value = mock_deployment_instance
        
        result = self.runner.invoke(app, ["deploy"])
        
        assert result.exit_code == 0
        assert "🚀 开始部署到Worker节点" in result.stdout
        assert "✅ 所有节点部署成功" in result.stdout
    
    @patch('sage.cli.worker_manager.execute_remote_command')
    @patch('sage.cli.worker_manager.DeploymentManager')
    @patch('sage.cli.worker_manager.get_config_manager')
    def test_add_worker_success(self, mock_get_config_manager, mock_deployment_manager, mock_execute_remote):
        """Test successful worker addition"""
        mock_config_manager = MagicMock()
        mock_config_manager.add_worker_ssh_host.return_value = True
        mock_config_manager.get_head_config.return_value = {
            'host': 'head-node',
            'head_port': 6379
        }
        mock_config_manager.get_worker_config.return_value = {
            'bind_host': 'localhost',
            'temp_dir': '/tmp/ray_worker',
            'log_dir': '/tmp/sage_worker_logs'
        }
        mock_config_manager.get_remote_config.return_value = {
            'ray_command': '/opt/conda/envs/sage/bin/ray',
            'conda_env': 'sage'
        }
        mock_get_config_manager.return_value = mock_config_manager
        
        mock_deployment_instance = MagicMock()
        mock_deployment_instance.deploy_to_worker.return_value = True
        mock_deployment_manager.return_value = mock_deployment_instance
        
        mock_execute_remote.return_value = True
        
        result = self.runner.invoke(app, ["add", "newworker:22"])
        
        assert result.exit_code == 0
        assert "➕ 添加新Worker节点: newworker:22" in result.stdout
        mock_config_manager.add_worker_ssh_host.assert_called_with('newworker', 22)
    
    @patch('sage.cli.worker_manager.execute_remote_command')
    @patch('sage.cli.worker_manager.get_config_manager')
    def test_remove_worker_success(self, mock_get_config_manager, mock_execute_remote):
        """Test successful worker removal"""
        mock_config_manager = MagicMock()
        mock_config_manager.remove_worker_ssh_host.return_value = True
        mock_config_manager.get_worker_config.return_value = {
            'temp_dir': '/tmp/ray_worker',
            'log_dir': '/tmp/sage_worker_logs'
        }
        mock_config_manager.get_remote_config.return_value = {
            'ray_command': '/opt/conda/envs/sage/bin/ray',
            'conda_env': 'sage'
        }
        mock_get_config_manager.return_value = mock_config_manager
        
        mock_execute_remote.return_value = True
        
        result = self.runner.invoke(app, ["remove", "oldworker:22"])
        
        assert result.exit_code == 0
        assert "➖ 移除Worker节点: oldworker:22" in result.stdout
        mock_config_manager.remove_worker_ssh_host.assert_called_with('oldworker', 22)
    
    def test_add_worker_invalid_port(self):
        """Test adding worker with invalid port"""
        result = self.runner.invoke(app, ["add", "worker:abc"])
        
        assert result.exit_code == 1
        assert "❌ 端口号必须是数字" in result.stdout
    
    def test_remove_worker_invalid_port(self):
        """Test removing worker with invalid port"""
        result = self.runner.invoke(app, ["remove", "worker:abc"])
        
        assert result.exit_code == 1
        assert "❌ 端口号必须是数字" in result.stdout
