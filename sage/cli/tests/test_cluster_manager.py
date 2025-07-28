"""
Test module for cluster_manager CLI commands
"""
import pytest
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner

from sage.cli.cluster_manager import app


class TestClusterManager:
    def setup_method(self):
        self.runner = CliRunner()
    
    @patch('sage.cli.cluster_manager.get_config_manager')
    def test_show_info(self, mock_get_config_manager):
        """Test showing cluster information"""
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
        mock_config_manager.get_workers_ssh_hosts.return_value = [
            ('worker1', 22),
            ('worker2', 8022)
        ]
        mock_config_manager.get_ssh_config.return_value = {
            'user': 'sage',
            'key_path': '~/.ssh/id_rsa'
        }
        mock_config_manager.get_remote_config.return_value = {
            'sage_home': '/home/sage',
            'python_path': '/opt/conda/envs/sage/bin/python'
        }
        mock_get_config_manager.return_value = mock_config_manager
        
        result = self.runner.invoke(app, ["info"])
        
        assert result.exit_code == 0
        assert "Ray集群配置信息" in result.stdout
        assert "head-node" in result.stdout
    
    @patch('sage.cli.cluster_manager.DeploymentManager')
    def test_deploy_cluster_success(self, mock_deployment_class):
        """Test successful cluster deployment"""
        mock_deployment_manager = MagicMock()
        mock_deployment_manager.deploy_to_all_workers.return_value = (2, 2)
        mock_deployment_class.return_value = mock_deployment_manager
        
        result = self.runner.invoke(app, ["deploy"])
        
        assert result.exit_code == 0
        assert "集群部署成功" in result.stdout
    
    @patch('sage.cli.cluster_manager.DeploymentManager')
    def test_deploy_cluster_partial_failure(self, mock_deployment_class):
        """Test cluster deployment with partial failure"""
        mock_deployment_manager = MagicMock()
        mock_deployment_manager.deploy_to_all_workers.return_value = (1, 2)
        mock_deployment_class.return_value = mock_deployment_manager
        
        result = self.runner.invoke(app, ["deploy"])
        
        assert result.exit_code == 1
        assert "部分节点部署失败" in result.stdout
    
    @patch('time.sleep')
    @patch('sage.cli.head_manager.start_head')
    @patch('sage.cli.worker_manager.start_workers')
    def test_start_cluster_success(self, mock_start_workers, mock_start_head, mock_sleep):
        """Test successful cluster start"""
        result = self.runner.invoke(app, ["start"])
        
        assert result.exit_code == 0
        assert "启动Ray集群" in result.stdout
        assert "集群启动完成" in result.stdout
        mock_start_head.assert_called_once()
        mock_start_workers.assert_called_once()
    
    @patch('sage.cli.head_manager.start_head')
    def test_start_cluster_head_failure(self, mock_start_head):
        """Test cluster start with head failure"""
        mock_start_head.side_effect = Exception("Head start failed")
        
        result = self.runner.invoke(app, ["start"])
        
        assert result.exit_code == 1
        assert "Head节点启动失败" in result.stdout
    
    @patch('time.sleep')
    @patch('sage.cli.head_manager.stop_head')
    @patch('sage.cli.worker_manager.stop_workers')
    def test_stop_cluster_success(self, mock_stop_workers, mock_stop_head, mock_sleep):
        """Test successful cluster stop"""
        result = self.runner.invoke(app, ["stop"])
        
        assert result.exit_code == 0
        assert "停止Ray集群" in result.stdout
        assert "集群停止完成" in result.stdout
        mock_stop_workers.assert_called_once()
        mock_stop_head.assert_called_once()
    
    @patch('sage.cli.worker_manager.status_workers')
    @patch('sage.cli.head_manager.status_head')
    @patch('sage.cli.cluster_manager.get_config_manager')
    def test_status_cluster(self, mock_get_config_manager, mock_status_head, mock_status_workers):
        """Test cluster status check"""
        mock_config_manager = MagicMock()
        mock_config_manager.get_head_config.return_value = {
            'host': 'head-node',
            'head_port': 6379,
            'dashboard_port': 8265
        }
        mock_config_manager.get_workers_ssh_hosts.return_value = [('worker1', 22)]
        mock_get_config_manager.return_value = mock_config_manager
        
        # mock successful head status
        mock_status_head.return_value = None
        
        result = self.runner.invoke(app, ["status"])
        
        assert result.exit_code == 0
        assert "检查Ray集群状态" in result.stdout
        mock_status_head.assert_called_once()
        mock_status_workers.assert_called_once()
    
    @patch('time.sleep')
    @patch('sage.cli.cluster_manager.start_cluster')
    @patch('sage.cli.cluster_manager.stop_cluster')
    def test_restart_cluster(self, mock_stop_cluster, mock_start_cluster, mock_sleep):
        """Test cluster restart"""
        result = self.runner.invoke(app, ["restart"])
        
        assert result.exit_code == 0
        assert "重启Ray集群" in result.stdout
        assert "集群重启完成" in result.stdout
    
    @patch('sage.cli.worker_manager.add_worker')
    def test_scale_add_worker(self, mock_add_worker):
        """Test adding worker to cluster"""
        result = self.runner.invoke(app, ["scale", "add", "newworker:22"])
        
        assert result.exit_code == 0
        assert "扩容集群" in result.stdout
        assert "newworker:22" in result.stdout
        mock_add_worker.assert_called_once_with("newworker:22")
    
    @patch('sage.cli.worker_manager.remove_worker')
    def test_scale_remove_worker(self, mock_remove_worker):
        """Test removing worker from cluster"""
        result = self.runner.invoke(app, ["scale", "remove", "worker1:22"])
        
        assert result.exit_code == 0
        assert "缩容集群" in result.stdout
        assert "worker1:22" in result.stdout
        mock_remove_worker.assert_called_once_with("worker1:22")
    
    def test_scale_invalid_action(self):
        """Test scale with invalid action"""
        result = self.runner.invoke(app, ["scale", "invalid", "worker:22"])
        
        assert result.exit_code == 1
        assert "操作必须是" in result.stdout
