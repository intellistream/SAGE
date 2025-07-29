"""
Tests for sage.cli.config_manager
"""
import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
import yaml

from sage.cli.config_manager import ConfigManager


class TestConfigManager:
    """Test ConfigManager class"""
    
    def test_init_with_custom_path(self):
        """Test initialization with custom config path"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump({'test': 'value'}, f)
            config_path = f.name
        
        try:
            manager = ConfigManager(config_path)
            assert manager.config_path == Path(config_path)
        finally:
            os.unlink(config_path)
    
    def test_init_with_home_config(self):
        """Test initialization with home directory config"""
        manager = ConfigManager()
        expected_path = Path.home() / ".sage" / "config.yaml"
        assert manager.config_path == expected_path
    
    def test_load_config_existing(self):
        """Test loading existing config file"""
        test_config = {
            'head': {'host': 'test-host', 'head_port': 6379},
            'workers_ssh_hosts': 'host1:22,host2:22'
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(test_config, f)
            config_path = f.name
        
        try:
            manager = ConfigManager(config_path)
            config = manager.load_config()
            
            assert config['head']['host'] == 'test-host'
            assert config['head']['head_port'] == 6379
            assert config['workers_ssh_hosts'] == 'host1:22,host2:22'
        finally:
            os.unlink(config_path)
    
    def test_load_config_nonexistent(self):
        """Test loading non-existent config creates default"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "nonexistent.yaml"
            manager = ConfigManager(str(config_path))
            
            # 应该抛出FileNotFoundError
            import pytest
            with pytest.raises(FileNotFoundError):
                manager.load_config()
    
    def test_get_head_config(self):
        """Test getting head configuration"""
        test_config = {
            'head': {
                'host': 'test-head',
                'head_port': 6379,
                'dashboard_port': 8265
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(test_config, f)
            config_path = f.name
        
        try:
            manager = ConfigManager(config_path)
            head_config = manager.get_head_config()
            
            assert head_config['host'] == 'test-head'
            assert head_config['head_port'] == 6379
            assert head_config['dashboard_port'] == 8265
        finally:
            os.unlink(config_path)
    
    def test_get_worker_config(self):
        """Test getting worker configuration"""
        test_config = {
            'worker': {
                'bind_host': 'localhost',
                'temp_dir': '/tmp/test_ray_worker'
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(test_config, f)
            config_path = f.name
        
        try:
            manager = ConfigManager(config_path)
            worker_config = manager.get_worker_config()
            
            assert worker_config['bind_host'] == 'localhost'
            assert worker_config['temp_dir'] == '/tmp/test_ray_worker'
        finally:
            os.unlink(config_path)
    
    def test_get_workers_ssh_hosts_string_format(self):
        """Test parsing workers SSH hosts from string format"""
        test_config = {
            'workers_ssh_hosts': 'host1:22,host2:8022,host3'
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(test_config, f)
            config_path = f.name
        
        try:
            manager = ConfigManager(config_path)
            workers = manager.get_workers_ssh_hosts()
            
            expected = [
                ('host1', 22),
                ('host2', 8022),
                ('host3', 22)  # Default port
            ]
            assert workers == expected
        finally:
            os.unlink(config_path)
    
    def test_get_workers_ssh_hosts_list_format(self):
        """Test parsing workers SSH hosts from list format"""
        test_config = {
            'workers_ssh_hosts': [
                {'host': 'host1', 'port': 22},
                {'host': 'host2', 'port': 8022}
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(test_config, f)
            config_path = f.name
        
        try:
            manager = ConfigManager(config_path)
            workers = manager.get_workers_ssh_hosts()
            
            expected = [
                ('host1', 22),
                ('host2', 8022)
            ]
            assert workers == expected
        finally:
            os.unlink(config_path)
    
    def test_add_worker_ssh_host(self):
        """Test adding worker SSH host"""
        test_config = {
            'workers_ssh_hosts': 'host1:22'
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(test_config, f)
            config_path = f.name
        
        try:
            manager = ConfigManager(config_path)
            
            # Add new host
            result = manager.add_worker_ssh_host('host2', 8022)
            assert result is True
            
            workers = manager.get_workers_ssh_hosts()
            assert ('host2', 8022) in workers
            
            # Try to add existing host
            result = manager.add_worker_ssh_host('host2', 8022)
            assert result is False
        finally:
            os.unlink(config_path)
    
    def test_remove_worker_ssh_host(self):
        """Test removing worker SSH host"""
        test_config = {
            'workers_ssh_hosts': 'host1:22,host2:8022'
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(test_config, f)
            config_path = f.name
        
        try:
            manager = ConfigManager(config_path)
            
            # Remove existing host
            result = manager.remove_worker_ssh_host('host2', 8022)
            assert result is True
            
            workers = manager.get_workers_ssh_hosts()
            assert ('host2', 8022) not in workers
            assert ('host1', 22) in workers
            
            # Try to remove non-existent host
            result = manager.remove_worker_ssh_host('host3', 22)
            assert result is False
        finally:
            os.unlink(config_path)
    
    def test_get_ssh_config(self):
        """Test getting SSH configuration"""
        test_config = {
            'ssh': {
                'user': 'testuser',
                'key_path': '~/.ssh/test_rsa',
                'connect_timeout': 15
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(test_config, f)
            config_path = f.name
        
        try:
            manager = ConfigManager(config_path)
            ssh_config = manager.get_ssh_config()
            
            assert ssh_config['user'] == 'testuser'
            assert ssh_config['key_path'] == '~/.ssh/test_rsa'
            assert ssh_config['connect_timeout'] == 15
        finally:
            os.unlink(config_path)
    
    def test_get_remote_config(self):
        """Test getting remote configuration"""
        test_config = {
            'remote': {
                'sage_home': '/home/testuser',
                'python_path': '/opt/conda/bin/python',
                'conda_env': 'test_env'
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(test_config, f)
            config_path = f.name
        
        try:
            manager = ConfigManager(config_path)
            remote_config = manager.get_remote_config()
            
            assert remote_config['sage_home'] == '/home/testuser'
            assert remote_config['python_path'] == '/opt/conda/bin/python'
            assert remote_config['conda_env'] == 'test_env'
        finally:
            os.unlink(config_path)
