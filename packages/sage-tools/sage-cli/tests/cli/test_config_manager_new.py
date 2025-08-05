#!/usr/bin/env python3
"""
Tests for sage.cli.config_manager
完整测试配置管理器功能
"""

import pytest
import yaml
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock

from sage.cli.config_manager import ConfigManager, get_config_manager


class TestConfigManagerInit:
    """Test ConfigManager class initialization"""
    
    @pytest.mark.unit
    def test_init_with_custom_path(self):
        """测试使用自定义路径初始化配置管理器"""
        custom_path = "/custom/config.yaml"
        config_manager = ConfigManager(custom_path)
        
        assert config_manager.config_path == Path(custom_path)
        assert config_manager._config is None
    
    @pytest.mark.unit
    def test_init_with_default_path(self):
        """测试使用默认路径初始化配置管理器"""
        config_manager = ConfigManager()
        
        expected_path = Path.home() / ".sage" / "config.yaml"
        assert config_manager.config_path == expected_path
        assert config_manager._config is None


class TestConfigManagerLoad:
    """Test config loading functionality"""
    
    @pytest.mark.unit
    @patch('pathlib.Path.exists', return_value=True)
    def test_load_config_success(self, mock_exists):
        """测试成功加载配置文件"""
        test_config = {
            'daemon': {'host': '127.0.0.1', 'port': 19001},
            'output': {'format': 'table', 'colors': True}
        }
        
        with patch('builtins.open', mock_open(read_data=yaml.dump(test_config))):
            config_manager = ConfigManager("/test/config.yaml")
            loaded_config = config_manager.load_config()
            
            assert loaded_config == test_config
            assert config_manager._config == test_config
    
    @pytest.mark.unit
    @patch('pathlib.Path.exists', return_value=False)
    def test_load_config_file_not_found(self, mock_exists):
        """测试配置文件不存在时的错误处理"""
        config_manager = ConfigManager("/nonexistent/config.yaml")
        
        with pytest.raises(FileNotFoundError, match="配置文件不存在"):
            config_manager.load_config()
    
    @pytest.mark.unit
    @patch('pathlib.Path.exists', return_value=True)
    def test_load_config_yaml_error(self, mock_exists):
        """测试YAML解析错误的处理"""
        invalid_yaml = "invalid: yaml: content: ["
        
        with patch('builtins.open', mock_open(read_data=invalid_yaml)):
            config_manager = ConfigManager("/test/config.yaml")
            
            with pytest.raises(RuntimeError, match="加载配置文件失败"):
                config_manager.load_config()
    
    @pytest.mark.unit
    @patch('pathlib.Path.exists', return_value=True)
    def test_load_config_io_error(self, mock_exists):
        """测试文件IO错误的处理"""
        with patch('builtins.open', side_effect=IOError("Permission denied")):
            config_manager = ConfigManager("/test/config.yaml")
            
            with pytest.raises(RuntimeError, match="加载配置文件失败"):
                config_manager.load_config()


class TestConfigManagerSave:
    """Test config saving functionality"""
    
    @pytest.mark.unit
    @patch('pathlib.Path.mkdir')
    def test_save_config_success(self, mock_mkdir):
        """测试成功保存配置文件"""
        test_config = {
            'daemon': {'host': '127.0.0.1', 'port': 19001},
            'output': {'format': 'table'}
        }
        
        with patch('builtins.open', mock_open()) as mock_file:
            config_manager = ConfigManager("/test/config.yaml")
            config_manager.save_config(test_config)
            
            # 验证目录创建
            mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
            
            # 验证文件写入
            mock_file.assert_called_once_with(config_manager.config_path, 'w', encoding='utf-8')
            
            # 验证配置被缓存
            assert config_manager._config == test_config
    
    @pytest.mark.unit
    @patch('pathlib.Path.mkdir')
    def test_save_config_io_error(self, mock_mkdir):
        """测试保存配置文件时的IO错误处理"""
        test_config = {'test': 'config'}
        
        with patch('builtins.open', side_effect=IOError("Permission denied")):
            config_manager = ConfigManager("/test/config.yaml")
            
            with pytest.raises(RuntimeError, match="保存配置文件失败"):
                config_manager.save_config(test_config)


class TestConfigManagerProperty:
    """Test config property functionality"""
    
    @pytest.mark.unit
    @patch('pathlib.Path.exists', return_value=True)
    def test_config_property_loads_if_none(self, mock_exists):
        """测试config属性在未加载时自动加载配置"""
        test_config = {'test': 'data'}
        
        with patch('builtins.open', mock_open(read_data=yaml.dump(test_config))):
            config_manager = ConfigManager("/test/config.yaml")
            
            # config属性应该自动加载配置
            assert config_manager.config == test_config
            assert config_manager._config == test_config
    
    @pytest.mark.unit
    def test_config_property_returns_cached(self):
        """测试config属性返回已缓存的配置"""
        test_config = {'test': 'data'}
        config_manager = ConfigManager("/test/config.yaml")
        config_manager._config = test_config  # 手动设置缓存
        
        # 应该返回缓存的配置，不重新加载
        assert config_manager.config == test_config


class TestConfigGetters:
    """Test config-specific getter methods"""
    
    def setup_method(self):
        """Setup test config"""
        self.test_config = {
            'daemon': {
                'host': '127.0.0.1',
                'port': 19001
            },
            'workers': {
                'head_node': 'base-sage',
                'worker_nodes': 'sage2:22,sage4:22',
                'ssh_user': 'sage',
                'ssh_key_path': '~/.ssh/id_rsa',
                'head_port': 6379
            },
            'head': {
                'host': 'localhost',
                'head_port': 6379,
                'dashboard_port': 8265,
                'dashboard_host': '0.0.0.0',
                'temp_dir': '/tmp/ray_head',
                'log_dir': '/tmp/sage_head_logs'
            },
            'remote': {
                'ray_command': '/opt/conda/envs/sage/bin/ray',
                'conda_env': 'sage'
            }
        }
    
    @pytest.mark.unit
    def test_get_daemon_config(self):
        """测试获取daemon配置"""
        with patch.object(ConfigManager, 'config', self.test_config):
            config_manager = ConfigManager()
            daemon_config = config_manager.get_daemon_config()
            
            assert daemon_config == self.test_config['daemon']
            assert daemon_config['host'] == '127.0.0.1'
            assert daemon_config['port'] == 19001
    
    @pytest.mark.unit
    def test_get_worker_config(self):
        """测试获取worker配置"""
        with patch.object(ConfigManager, 'config', self.test_config):
            config_manager = ConfigManager()
            worker_config = config_manager.get_worker_config()
            
            assert worker_config == self.test_config['workers']
            assert worker_config['head_node'] == 'base-sage'
    
    @pytest.mark.unit
    def test_get_head_config(self):
        """测试获取head配置"""
        with patch.object(ConfigManager, 'config', self.test_config):
            config_manager = ConfigManager()
            head_config = config_manager.get_head_config()
            
            assert head_config == self.test_config['head']
            assert head_config['dashboard_port'] == 8265
    
    @pytest.mark.unit
    def test_get_remote_config(self):
        """测试获取remote配置"""
        with patch.object(ConfigManager, 'config', self.test_config):
            config_manager = ConfigManager()
            remote_config = config_manager.get_remote_config()
            
            assert remote_config == self.test_config['remote']
            assert remote_config['conda_env'] == 'sage'
    
    @pytest.mark.unit
    def test_get_config_missing_section(self):
        """测试获取不存在的配置段时返回空字典"""
        minimal_config = {'daemon': {'host': 'localhost'}}
        
        with patch.object(ConfigManager, 'config', minimal_config):
            config_manager = ConfigManager()
            
            assert config_manager.get_worker_config() == {}
            assert config_manager.get_head_config() == {}
            assert config_manager.get_remote_config() == {}


class TestGetConfigManagerFunction:
    """Test get_config_manager function"""
    
    @pytest.mark.unit
    @patch('sage.cli.config_manager.ConfigManager')
    def test_get_config_manager_default(self, mock_config_manager_class):
        """测试获取默认配置管理器"""
        mock_instance = MagicMock()
        mock_config_manager_class.return_value = mock_instance
        
        result = get_config_manager()
        
        mock_config_manager_class.assert_called_once_with()
        assert result == mock_instance
    
    @pytest.mark.unit
    @patch('sage.cli.config_manager.ConfigManager')
    def test_get_config_manager_with_path(self, mock_config_manager_class):
        """测试使用自定义路径获取配置管理器"""
        mock_instance = MagicMock()
        mock_config_manager_class.return_value = mock_instance
        custom_path = "/custom/config.yaml"
        
        result = get_config_manager(custom_path)
        
        mock_config_manager_class.assert_called_once_with(custom_path)
        assert result == mock_instance


class TestIntegration:
    """Integration tests for config manager"""
    
    @pytest.mark.integration
    def test_full_config_lifecycle(self):
        """测试配置的完整生命周期：创建、保存、加载"""
        test_config = {
            'daemon': {'host': '127.0.0.1', 'port': 19001},
            'output': {'format': 'table', 'colors': True},
            'test_section': {'test_key': 'test_value'}
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "test_config.yaml"
            
            # 创建配置管理器并保存配置
            config_manager = ConfigManager(str(config_path))
            config_manager.save_config(test_config)
            
            # 验证文件存在
            assert config_path.exists()
            
            # 创建新的配置管理器并加载配置
            new_config_manager = ConfigManager(str(config_path))
            loaded_config = new_config_manager.load_config()
            
            # 验证配置内容正确
            assert loaded_config == test_config
            
            # 验证通过属性访问也正确
            assert new_config_manager.config == test_config
    
    @pytest.mark.integration
    def test_config_yaml_format(self):
        """测试配置文件YAML格式正确性"""
        test_config = {
            'daemon': {'host': '127.0.0.1', 'port': 19001},
            'nested': {
                'level1': {
                    'level2': ['item1', 'item2', 'item3']
                }
            }
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "test_config.yaml"
            config_manager = ConfigManager(str(config_path))
            
            # 保存配置
            config_manager.save_config(test_config)
            
            # 直接读取文件内容验证YAML格式
            with open(config_path, 'r', encoding='utf-8') as f:
                file_content = f.read()
            
            # 验证YAML格式
            assert 'daemon:' in file_content
            assert 'host: 127.0.0.1' in file_content
            assert 'port: 19001' in file_content
            
            # 验证可以被标准YAML解析器解析
            parsed_config = yaml.safe_load(file_content)
            assert parsed_config == test_config
    
    @pytest.mark.integration
    @pytest.mark.slow
    def test_config_thread_safety(self):
        """测试配置管理器的线程安全性"""
        import threading
        import time
        
        test_config = {'counter': 0}
        
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "thread_test_config.yaml"
            config_manager = ConfigManager(str(config_path))
            config_manager.save_config(test_config)
            
            results = []
            errors = []
            
            def worker():
                try:
                    worker_config_manager = ConfigManager(str(config_path))
                    loaded_config = worker_config_manager.load_config()
                    results.append(loaded_config)
                except Exception as e:
                    errors.append(e)
            
            # 创建多个线程同时访问配置
            threads = []
            for _ in range(5):
                thread = threading.Thread(target=worker)
                threads.append(thread)
                thread.start()
            
            # 等待所有线程完成
            for thread in threads:
                thread.join()
            
            # 验证结果
            assert len(errors) == 0, f"Errors occurred: {errors}"
            assert len(results) == 5
            for result in results:
                assert result == test_config
