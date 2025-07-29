"""
Tests for sage.cli.deployment_manager
"""
import pytest
import tempfile
import os
import tarfile
from pathlib import Path
from unittest.mock import patch, MagicMock, call
from typer.testing import CliRunner

from sage.cli.deployment_manager import DeploymentManager


class TestDeploymentManager:
    """Test DeploymentManager class"""
    
    @patch('sage.cli.deployment_manager.get_config_manager')
    def test_init(self, mock_get_config_manager):
        """Test DeploymentManager initialization"""
        mock_config_manager = MagicMock()
        mock_get_config_manager.return_value = mock_config_manager
        
        manager = DeploymentManager()
        
        assert manager.config_manager == mock_config_manager
        assert manager.project_root.name == "SAGE"
    
    @patch('sage.cli.deployment_manager.get_config_manager')
    def test_create_deployment_package(self, mock_get_config_manager):
        """Test creating deployment package"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create mock project structure
            project_root = Path(temp_dir) / "SAGE"
            project_root.mkdir()
            
            # Create required directories and files
            (project_root / "sage").mkdir()
            (project_root / "app").mkdir()
            (project_root / "config").mkdir()
            (project_root / "frontend").mkdir()
            (project_root / "installation").mkdir()
            
            (project_root / "setup.py").touch()
            (project_root / "README.md").touch()
            (project_root / "LICENSE").touch()
            
            # Mock the deployment manager
            manager = DeploymentManager()
            manager.project_root = project_root
            
            package_path = manager.create_deployment_package()
            
            # Verify package was created
            assert os.path.exists(package_path)
            assert package_path.endswith('.tar.gz')
            
            # Verify package contents
            with tarfile.open(package_path, 'r:gz') as tar:
                names = tar.getnames()
                assert 'sage' in names
                assert 'app' in names
                assert 'config' in names
                assert 'frontend' in names
                assert 'installation' in names
                assert 'setup.py' in names
                assert 'README.md' in names
                assert 'LICENSE' in names
    
    @patch('sage.cli.deployment_manager.subprocess.run')
    @patch('sage.cli.deployment_manager.get_config_manager')
    def test_execute_ssh_command_success(self, mock_get_config_manager, mock_subprocess):
        """Test successful SSH command execution"""
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
        
        manager = DeploymentManager()
        result = manager.execute_ssh_command('testhost', 22, 'echo "test"')
        
        assert result is True
        mock_subprocess.assert_called_once()
    
    @patch('sage.cli.deployment_manager.subprocess.run')
    @patch('sage.cli.deployment_manager.get_config_manager')
    def test_execute_ssh_command_failure(self, mock_get_config_manager, mock_subprocess):
        """Test failed SSH command execution"""
        mock_config_manager = MagicMock()
        mock_config_manager.get_ssh_config.return_value = {
            'user': 'testuser',
            'key_path': '~/.ssh/id_rsa',
            'connect_timeout': 10
        }
        mock_get_config_manager.return_value = mock_config_manager
        
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "Command failed"
        mock_subprocess.return_value = mock_result
        
        manager = DeploymentManager()
        result = manager.execute_ssh_command('testhost', 22, 'false')
        
        assert result is False
    
    @patch('sage.cli.deployment_manager.subprocess.run')
    @patch('sage.cli.deployment_manager.get_config_manager')
    def test_transfer_file_success(self, mock_get_config_manager, mock_subprocess):
        """Test successful file transfer"""
        mock_config_manager = MagicMock()
        mock_config_manager.get_ssh_config.return_value = {
            'user': 'testuser',
            'key_path': '~/.ssh/id_rsa',
            'connect_timeout': 10
        }
        mock_get_config_manager.return_value = mock_config_manager
        
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result
        
        manager = DeploymentManager()
        
        with tempfile.NamedTemporaryFile() as temp_file:
            result = manager.transfer_file(temp_file.name, 'testhost', 22, '/tmp/test')
            
            assert result is True
            mock_subprocess.assert_called_once()
    
    @patch('sage.cli.deployment_manager.subprocess.run')
    @patch('sage.cli.deployment_manager.get_config_manager')
    def test_transfer_file_failure(self, mock_get_config_manager, mock_subprocess):
        """Test failed file transfer"""
        mock_config_manager = MagicMock()
        mock_config_manager.get_ssh_config.return_value = {
            'user': 'testuser',
            'key_path': '~/.ssh/id_rsa',
            'connect_timeout': 10
        }
        mock_get_config_manager.return_value = mock_config_manager
        
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "Transfer failed"
        mock_subprocess.return_value = mock_result
        
        manager = DeploymentManager()
        
        with tempfile.NamedTemporaryFile() as temp_file:
            result = manager.transfer_file(temp_file.name, 'testhost', 22, '/tmp/test')
            
            assert result is False
    
    @patch.object(DeploymentManager, 'execute_ssh_command')
    @patch.object(DeploymentManager, 'transfer_file')
    @patch.object(DeploymentManager, 'create_deployment_package')
    @patch('sage.cli.deployment_manager.get_config_manager')
    def test_deploy_to_worker_success(self, mock_get_config_manager, mock_create_package, 
                                      mock_transfer_file, mock_execute_ssh):
        """Test successful worker deployment"""
        mock_config_manager = MagicMock()
        mock_config_manager.get_remote_config.return_value = {
            'sage_home': '/home/sage',
            'python_path': '/opt/conda/envs/sage/bin/python',
            'conda_env': 'sage'
        }
        mock_config_manager.config_path = MagicMock()
        mock_config_manager.config_path.exists.return_value = True
        mock_get_config_manager.return_value = mock_config_manager
        
        mock_create_package.return_value = '/tmp/test_package.tar.gz'
        mock_transfer_file.return_value = True
        mock_execute_ssh.return_value = True
        
        manager = DeploymentManager()
        result = manager.deploy_to_worker('testhost', 22)
        
        assert result is True
        mock_create_package.assert_called_once()
        assert mock_transfer_file.call_count >= 1  # Package + config file
        mock_execute_ssh.assert_called()
    
    @patch.object(DeploymentManager, 'transfer_file')
    @patch.object(DeploymentManager, 'create_deployment_package')
    @patch('sage.cli.deployment_manager.get_config_manager')
    def test_deploy_to_worker_transfer_failure(self, mock_get_config_manager, 
                                               mock_create_package, mock_transfer_file):
        """Test worker deployment with transfer failure"""
        mock_config_manager = MagicMock()
        mock_get_config_manager.return_value = mock_config_manager
        
        mock_create_package.return_value = '/tmp/test_package.tar.gz'
        mock_transfer_file.return_value = False  # Transfer fails
        
        manager = DeploymentManager()
        result = manager.deploy_to_worker('testhost', 22)
        
        assert result is False
    
    @patch.object(DeploymentManager, 'deploy_to_worker')
    @patch('sage.cli.deployment_manager.get_config_manager')
    def test_deploy_to_all_workers(self, mock_get_config_manager, mock_deploy_to_worker):
        """Test deploying to all workers"""
        mock_config_manager = MagicMock()
        mock_config_manager.get_workers_ssh_hosts.return_value = [
            ('host1', 22),
            ('host2', 8022)
        ]
        mock_get_config_manager.return_value = mock_config_manager
        
        mock_deploy_to_worker.side_effect = [True, True]  # Both succeed
        
        manager = DeploymentManager()
        success_count, total_count = manager.deploy_to_all_workers()
        
        assert success_count == 2
        assert total_count == 2
        assert mock_deploy_to_worker.call_count == 2
    
    @patch.object(DeploymentManager, 'deploy_to_worker')
    @patch('sage.cli.deployment_manager.get_config_manager')
    def test_deploy_to_all_workers_partial_failure(self, mock_get_config_manager, 
                                                    mock_deploy_to_worker):
        """Test deploying to all workers with partial failure"""
        mock_config_manager = MagicMock()
        mock_config_manager.get_workers_ssh_hosts.return_value = [
            ('host1', 22),
            ('host2', 8022)
        ]
        mock_get_config_manager.return_value = mock_config_manager
        
        mock_deploy_to_worker.side_effect = [True, False]  # Second fails
        
        manager = DeploymentManager()
        success_count, total_count = manager.deploy_to_all_workers()
        
        assert success_count == 1
        assert total_count == 2
    
    @patch('sage.cli.deployment_manager.get_config_manager')
    def test_deploy_to_all_workers_no_workers(self, mock_get_config_manager):
        """Test deploying when no workers are configured"""
        mock_config_manager = MagicMock()
        mock_config_manager.get_workers_ssh_hosts.return_value = []
        mock_get_config_manager.return_value = mock_config_manager
        
        manager = DeploymentManager()
        success_count, total_count = manager.deploy_to_all_workers()
        
        assert success_count == 0
        assert total_count == 0
