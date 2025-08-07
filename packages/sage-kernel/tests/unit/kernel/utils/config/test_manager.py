"""
Tests for sage.utils.config.manager module
==========================================

单元测试配置管理器模块的功能，包括：
- ConfigManager类的所有方法
- 多种格式的配置文件支持 (YAML, JSON, TOML)
- 缓存机制
- 嵌套配置项的获取和设置
- BaseConfig类的验证功能
"""

import pytest
import tempfile
import json
import yaml
from pathlib import Path
from unittest.mock import patch, MagicMock
from pydantic import ValidationError

from sage.kernel.utils.config.manager import (
    ConfigManager, 
    BaseConfig, 
    load_config, 
    save_config
)


@pytest.mark.unit
class TestBaseConfig:
    """BaseConfig类测试"""
    
    def test_base_config_creation(self):
        """测试BaseConfig基本创建"""
        class TestConfig(BaseConfig):
            app_name: str = "test"
            debug: bool = False
        
        config = TestConfig()
        assert config.app_name == "test"
        assert config.debug is False
    
    def test_base_config_with_extra_fields(self):
        """测试BaseConfig允许额外字段"""
        class TestConfig(BaseConfig):
            app_name: str = "test"
        
        config = TestConfig(app_name="myapp", extra_field="extra_value")
        assert config.app_name == "myapp"
        assert config.extra_field == "extra_value"
    
    def test_base_config_validation(self):
        """测试BaseConfig字段验证"""
        class TestConfig(BaseConfig):
            app_name: str
            port: int
        
        # 正常情况
        config = TestConfig(app_name="test", port=8080)
        assert config.app_name == "test"
        assert config.port == 8080
        
        # 类型错误
        with pytest.raises(ValidationError):
            TestConfig(app_name="test", port="invalid")
    
    def test_base_config_assignment_validation(self):
        """测试BaseConfig赋值验证"""
        class TestConfig(BaseConfig):
            port: int = 8080
        
        config = TestConfig()
        config.port = 9000
        assert config.port == 9000
        
        # 赋值时类型验证
        with pytest.raises(ValidationError):
            config.port = "invalid"


@pytest.mark.unit
class TestConfigManager:
    """ConfigManager类测试"""
    
    def setup_method(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_dir = Path(self.temp_dir)
        self.manager = ConfigManager(self.config_dir)
        
        # 准备测试配置数据
        self.test_config = {
            "app": {
                "name": "SAGE",
                "version": "1.0.0",
                "debug": True
            },
            "database": {
                "host": "localhost",
                "port": 5432,
                "name": "sage_db"
            },
            "features": {
                "cache_enabled": True,
                "max_connections": 100
            }
        }
    
    def teardown_method(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_config_manager_initialization(self):
        """测试ConfigManager初始化"""
        assert self.manager.config_dir == self.config_dir
        assert self.config_dir.exists()
        assert isinstance(self.manager._cache, dict)
    
    def test_config_manager_default_config_dir(self):
        """测试ConfigManager默认配置目录"""
        with patch('pathlib.Path.cwd') as mock_cwd:
            mock_cwd.return_value = Path("/tmp/test")
            manager = ConfigManager()
            assert manager.config_dir == Path("/tmp/test/config")
    
    def test_load_yaml_config(self):
        """测试加载YAML配置文件"""
        config_file = self.config_dir / "test.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(self.test_config, f)
        
        loaded_config = self.manager.load("test.yaml")
        assert loaded_config == self.test_config
        assert loaded_config["app"]["name"] == "SAGE"
        assert loaded_config["database"]["port"] == 5432
    
    def test_load_json_config(self):
        """测试加载JSON配置文件"""
        config_file = self.config_dir / "test.json"
        with open(config_file, 'w') as f:
            json.dump(self.test_config, f)
        
        loaded_config = self.manager.load("test.json")
        assert loaded_config == self.test_config
    
    def test_load_toml_config(self):
        """测试加载TOML配置文件"""
        # 创建TOML兼容的配置
        toml_config = {
            "app_name": "SAGE",
            "version": "1.0.0",
            "debug": True
        }
        
        config_file = self.config_dir / "test.toml"
        try:
            import tomli_w
            with open(config_file, 'wb') as f:
                tomli_w.dump(toml_config, f)
            
            loaded_config = self.manager.load("test.toml")
            assert loaded_config["app_name"] == "SAGE"
        except ImportError:
            # 如果没有tomli_w，测试ImportError
            with open(config_file, 'w') as f:
                f.write("[app]\nname = 'SAGE'\n")
            
            with pytest.raises(ImportError, match="需要安装 tomli 库"):
                self.manager.load("test.toml")
    
    def test_load_unsupported_format(self):
        """测试加载不支持的格式"""
        config_file = self.config_dir / "test.txt"
        config_file.write_text("some content")
        
        with pytest.raises(ValueError, match="不支持的配置文件格式"):
            self.manager.load("test.txt")
    
    def test_load_file_not_found(self):
        """测试加载不存在的文件"""
        with pytest.raises(FileNotFoundError, match="配置文件未找到"):
            self.manager.load("nonexistent.yaml")
    
    def test_cache_mechanism(self):
        """测试配置缓存机制"""
        config_file = self.config_dir / "cache_test.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(self.test_config, f)
        
        # 第一次加载
        config1 = self.manager.load("cache_test.yaml", use_cache=True)
        assert "cache_test.yaml" in self.manager._cache
        
        # 修改文件内容
        modified_config = self.test_config.copy()
        modified_config["app"]["name"] = "Modified"
        with open(config_file, 'w') as f:
            yaml.dump(modified_config, f)
        
        # 使用缓存，应该返回原始内容
        config2 = self.manager.load("cache_test.yaml", use_cache=True)
        assert config2["app"]["name"] == "SAGE"
        
        # 不使用缓存，应该返回修改后的内容
        config3 = self.manager.load("cache_test.yaml", use_cache=False)
        assert config3["app"]["name"] == "Modified"
    
    def test_save_yaml_config(self):
        """测试保存YAML配置文件"""
        filename = "save_test.yaml"
        self.manager.save(filename, self.test_config)
        
        config_file = self.config_dir / filename
        assert config_file.exists()
        
        # 验证保存的内容
        with open(config_file, 'r') as f:
            saved_config = yaml.safe_load(f)
        assert saved_config == self.test_config
    
    def test_save_json_config(self):
        """测试保存JSON配置文件"""
        filename = "save_test.json"
        self.manager.save(filename, self.test_config)
        
        config_file = self.config_dir / filename
        assert config_file.exists()
        
        # 验证保存的内容
        with open(config_file, 'r') as f:
            saved_config = json.load(f)
        assert saved_config == self.test_config
    
    def test_save_toml_config(self):
        """测试保存TOML配置文件"""
        # TOML兼容的配置
        toml_config = {
            "app_name": "SAGE",
            "version": "1.0.0",
            "debug": True
        }
        
        filename = "save_test.toml"
        try:
            self.manager.save(filename, toml_config)
            
            config_file = self.config_dir / filename
            assert config_file.exists()
        except ImportError:
            # 如果没有tomli_w，测试ImportError
            with pytest.raises(ImportError, match="需要安装 tomli-w 库"):
                self.manager.save(filename, toml_config)
    
    def test_save_with_format_override(self):
        """测试强制指定保存格式"""
        filename = "test_file.conf"  # 不常见的扩展名
        self.manager.save(filename, self.test_config, format="yaml")
        
        config_file = self.config_dir / filename
        assert config_file.exists()
        
        # 验证保存为YAML格式
        with open(config_file, 'r') as f:
            content = f.read()
            assert "app:" in content  # YAML特征
    
    def test_get_simple_key(self):
        """测试获取简单配置项"""
        config_file = self.config_dir / "get_test.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(self.test_config, f)
        
        value = self.manager.get("get_test.yaml", "app.name")
        assert value == "SAGE"
        
        value = self.manager.get("get_test.yaml", "database.port")
        assert value == 5432
    
    def test_get_nested_key(self):
        """测试获取嵌套配置项"""
        config_file = self.config_dir / "nested_test.yaml"
        nested_config = {
            "level1": {
                "level2": {
                    "level3": {
                        "value": "deep_value"
                    }
                }
            }
        }
        with open(config_file, 'w') as f:
            yaml.dump(nested_config, f)
        
        value = self.manager.get("nested_test.yaml", "level1.level2.level3.value")
        assert value == "deep_value"
    
    def test_get_nonexistent_key(self):
        """测试获取不存在的配置项"""
        config_file = self.config_dir / "get_test.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(self.test_config, f)
        
        value = self.manager.get("get_test.yaml", "nonexistent.key", "default_value")
        assert value == "default_value"
        
        value = self.manager.get("get_test.yaml", "app.nonexistent", None)
        assert value is None
    
    def test_set_simple_key(self):
        """测试设置简单配置项"""
        filename = "set_test.yaml"
        
        # 设置新值
        self.manager.set(filename, "app.name", "NewName")
        self.manager.set(filename, "database.port", 3306)
        
        # 验证设置
        assert self.manager.get(filename, "app.name") == "NewName"
        assert self.manager.get(filename, "database.port") == 3306
    
    def test_set_nested_key(self):
        """测试设置嵌套配置项"""
        filename = "set_nested_test.yaml"
        
        self.manager.set(filename, "level1.level2.level3.value", "new_deep_value")
        
        value = self.manager.get(filename, "level1.level2.level3.value")
        assert value == "new_deep_value"
    
    def test_set_existing_config(self):
        """测试在现有配置文件中设置值"""
        filename = "existing_test.yaml"
        
        # 先保存初始配置
        self.manager.save(filename, self.test_config)
        
        # 修改现有值
        self.manager.set(filename, "app.name", "ModifiedName")
        self.manager.set(filename, "new_section.new_key", "new_value")
        
        # 验证修改
        assert self.manager.get(filename, "app.name") == "ModifiedName"
        assert self.manager.get(filename, "app.version") == "1.0.0"  # 未修改的值保持不变
        assert self.manager.get(filename, "new_section.new_key") == "new_value"
    
    def test_clear_cache(self):
        """测试清空缓存"""
        config_file = self.config_dir / "cache_clear_test.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(self.test_config, f)
        
        # 加载到缓存
        self.manager.load("cache_clear_test.yaml")
        assert "cache_clear_test.yaml" in self.manager._cache
        
        # 清空缓存
        self.manager.clear_cache()
        assert len(self.manager._cache) == 0
    
    def test_load_empty_config_file(self):
        """测试加载空配置文件"""
        config_file = self.config_dir / "empty.yaml"
        config_file.touch()
        
        config = self.manager.load("empty.yaml")
        assert config == {}


@pytest.mark.unit
class TestConvenienceFunctions:
    """便捷函数测试"""
    
    def setup_method(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_dir = Path(self.temp_dir)
        
        self.test_config = {
            "app_name": "TestApp",
            "version": "2.0.0"
        }
    
    def teardown_method(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_load_config_function_with_config_dir(self):
        """测试load_config便捷函数指定配置目录"""
        config_file = self.config_dir / "test.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(self.test_config, f)
        
        config = load_config("test.yaml", self.config_dir)
        assert config == self.test_config
    
    def test_load_config_function_global_manager(self):
        """测试load_config便捷函数使用全局管理器"""
        with patch('sage.kernel.utils.config.manager._global_config_manager') as mock_manager:
            mock_manager.load.return_value = self.test_config
            
            config = load_config("test.yaml")
            assert config == self.test_config
            mock_manager.load.assert_called_once_with("test.yaml")
    
    def test_save_config_function_with_config_dir(self):
        """测试save_config便捷函数指定配置目录"""
        save_config("test.yaml", self.test_config, self.config_dir)
        
        config_file = self.config_dir / "test.yaml"
        assert config_file.exists()
        
        with open(config_file, 'r') as f:
            saved_config = yaml.safe_load(f)
        assert saved_config == self.test_config
    
    def test_save_config_function_global_manager(self):
        """测试save_config便捷函数使用全局管理器"""
        with patch('sage.kernel.utils.config.manager._global_config_manager') as mock_manager:
            save_config("test.yaml", self.test_config)
            mock_manager.save.assert_called_once_with("test.yaml", self.test_config)


@pytest.mark.integration
class TestConfigManagerIntegration:
    """ConfigManager集成测试"""
    
    def test_real_world_config_workflow(self):
        """测试真实世界的配置工作流程"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ConfigManager(temp_dir)
            
            # 1. 创建初始配置
            initial_config = {
                "application": {
                    "name": "SAGE",
                    "version": "1.0.0",
                    "environment": "development"
                },
                "database": {
                    "host": "localhost",
                    "port": 5432,
                    "name": "sage_dev",
                    "pool_size": 10
                },
                "logging": {
                    "level": "DEBUG",
                    "handlers": ["console", "file"],
                    "file_path": "/var/log/sage.log"
                }
            }
            
            manager.save("app.yaml", initial_config)
            
            # 2. 读取和验证配置
            loaded_config = manager.load("app.yaml")
            assert loaded_config["application"]["name"] == "SAGE"
            assert loaded_config["database"]["pool_size"] == 10
            
            # 3. 更新部分配置
            manager.set("app.yaml", "application.environment", "production")
            manager.set("app.yaml", "database.host", "prod-db.example.com")
            manager.set("app.yaml", "logging.level", "INFO")
            
            # 4. 验证更新
            assert manager.get("app.yaml", "application.environment") == "production"
            assert manager.get("app.yaml", "database.host") == "prod-db.example.com"
            assert manager.get("app.yaml", "logging.level") == "INFO"
            
            # 5. 添加新的配置节
            manager.set("app.yaml", "cache.type", "redis")
            manager.set("app.yaml", "cache.host", "redis.example.com")
            manager.set("app.yaml", "cache.port", 6379)
            
            # 6. 验证完整配置
            final_config = manager.load("app.yaml")
            assert final_config["cache"]["type"] == "redis"
            assert final_config["cache"]["port"] == 6379
            
            # 7. 测试配置持久化
            manager2 = ConfigManager(temp_dir)
            reloaded_config = manager2.load("app.yaml")
            assert reloaded_config == final_config


# 性能测试
@pytest.mark.slow
class TestConfigManagerPerformance:
    """ConfigManager性能测试"""
    
    def test_large_config_file_performance(self):
        """测试大型配置文件的性能"""
        import time
        
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ConfigManager(temp_dir)
            
            # 创建大型配置
            large_config = {}
            for i in range(1000):
                large_config[f"section_{i}"] = {
                    f"key_{j}": f"value_{i}_{j}" for j in range(100)
                }
            
            # 测试保存性能
            start_time = time.time()
            manager.save("large_config.yaml", large_config)
            save_time = time.time() - start_time
            
            # 测试加载性能
            start_time = time.time()
            loaded_config = manager.load("large_config.yaml")
            load_time = time.time() - start_time
            
            # 基本性能断言（这些阈值可以根据实际需要调整）
            assert save_time < 20.0  # 保存应在20秒内完成（增加阈值以适应不同环境）
            assert load_time < 5.0  # 加载应在5秒内完成
            assert loaded_config == large_config
    
    def test_cache_performance(self):
        """测试缓存性能"""
        import time
        
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ConfigManager(temp_dir)
            
            # 创建一个包含1000个键值对的大配置字典
            config = {f"test_key_{i}": f"test_value_{i}" for i in range(1000)}
            manager.save("perf_test.yaml", config)
            
            # 第一次加载（无缓存）
            start_time = time.time()
            manager.load("perf_test.yaml", use_cache=False)
            first_load_time = time.time() - start_time
            
            # 第二次加载（有缓存）
            start_time = time.time()
            manager.load("perf_test.yaml", use_cache=True)
            cached_load_time = time.time() - start_time
            
            # 缓存应该显著提升性能
            assert cached_load_time < first_load_time / 2
