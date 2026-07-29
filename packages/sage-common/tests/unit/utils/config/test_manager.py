"""
Tests for sage.common.utils.config.manager

Tests configuration loading, saving, and management functionality.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from sage.common.utils.config.manager import (
    BaseConfig,
    ConfigManager,
    load_config,
    save_config,
)


class TestBaseConfig:
    """Tests for BaseConfig class"""

    def test_base_config_creation(self):
        """Test creating a base config"""
        config = BaseConfig()
        assert isinstance(config, BaseConfig)

    def test_base_config_with_fields(self):
        """Test base config allows extra fields"""

        class MyConfig(BaseConfig):
            name: str = "default"

        config = MyConfig(name="test", extra_field="value")
        assert config.name == "test"


class TestConfigManager:
    """Tests for ConfigManager class"""

    def test_initialization_default_dir(self):
        """Test initialization with default directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("sage.common.utils.config.manager.Path.cwd") as mock_cwd:
                mock_cwd.return_value = Path(tmpdir)
                manager = ConfigManager()

                assert manager.config_dir == Path(tmpdir) / "config"
                assert manager.config_dir.exists()

    def test_initialization_custom_dir(self):
        """Test initialization with custom directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "my_config"
            manager = ConfigManager(config_dir=config_dir)

            assert manager.config_dir == config_dir
            assert manager.config_dir.exists()

    def test_load_yaml_file(self):
        """Test loading YAML configuration"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            manager = ConfigManager(config_dir=config_dir)

            # Create test YAML file
            test_config = {"database": {"host": "localhost", "port": 5432}}
            config_file = config_dir / "test.yaml"
            with open(config_file, "w") as f:
                yaml.dump(test_config, f)

            # Load configuration
            loaded_config = manager.load("test.yaml")
            assert loaded_config == test_config

    def test_load_json_file(self):
        """Test loading JSON configuration"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            manager = ConfigManager(config_dir=config_dir)

            # Create test JSON file
            test_config = {"api": {"key": "12345", "url": "https://api.example.com"}}
            config_file = config_dir / "test.json"
            with open(config_file, "w") as f:
                json.dump(test_config, f)

            # Load configuration
            loaded_config = manager.load("test.json")
            assert loaded_config == test_config

    def test_load_with_cache(self):
        """Test loading with cache enabled"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            manager = ConfigManager(config_dir=config_dir)

            # Create test file
            test_config = {"value": 42}
            config_file = config_dir / "test.yaml"
            with open(config_file, "w") as f:
                yaml.dump(test_config, f)

            # Load twice
            config1 = manager.load("test.yaml", use_cache=True)
            config2 = manager.load("test.yaml", use_cache=True)

            assert config1 == config2
            assert "test.yaml" in manager._cache

    def test_load_file_not_found(self):
        """Test loading non-existent file raises error"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ConfigManager(config_dir=tmpdir)

            with pytest.raises(FileNotFoundError):
                manager.load("nonexistent.yaml")

    def test_load_unsupported_format(self):
        """Test loading unsupported file format"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            manager = ConfigManager(config_dir=config_dir)

            # Create file with unsupported extension
            config_file = config_dir / "test.txt"
            config_file.write_text("some content")

            with pytest.raises(ValueError, match="不支持的配置文件格式"):
                manager.load("test.txt")

    def test_save_yaml_file(self):
        """Test saving YAML configuration"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            manager = ConfigManager(config_dir=config_dir)

            # Save configuration
            test_config = {"server": {"host": "localhost", "port": 8080}}
            manager.save("test.yaml", test_config)

            # Verify file exists and content
            config_file = config_dir / "test.yaml"
            assert config_file.exists()

            with open(config_file) as f:
                loaded = yaml.safe_load(f)
                assert loaded == test_config

    def test_save_json_file(self):
        """Test saving JSON configuration"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            manager = ConfigManager(config_dir=config_dir)

            # Save configuration
            test_config = {"name": "test", "values": [1, 2, 3]}
            manager.save("test.json", test_config)

            # Verify file exists and content
            config_file = config_dir / "test.json"
            assert config_file.exists()

            with open(config_file) as f:
                loaded = json.load(f)
                assert loaded == test_config

    def test_save_with_forced_format(self):
        """Test saving with forced format"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            manager = ConfigManager(config_dir=config_dir)

            # Save as YAML even though extension is .conf
            test_config = {"key": "value"}
            manager.save("test.conf", test_config, format="yaml")

            config_file = config_dir / "test.conf"
            assert config_file.exists()

    def test_get_simple_key(self):
        """Test getting simple configuration key"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            manager = ConfigManager(config_dir=config_dir)

            # Create test file
            test_config = {"name": "test", "version": "1.0"}
            config_file = config_dir / "test.yaml"
            with open(config_file, "w") as f:
                yaml.dump(test_config, f)

            # Get value
            value = manager.get("test.yaml", "name")
            assert value == "test"

    def test_get_nested_key(self):
        """Test getting nested configuration key"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            manager = ConfigManager(config_dir=config_dir)

            # Create test file
            test_config = {"database": {"host": "localhost", "port": 5432}}
            config_file = config_dir / "test.yaml"
            with open(config_file, "w") as f:
                yaml.dump(test_config, f)

            # Get nested value
            value = manager.get("test.yaml", "database.host")
            assert value == "localhost"

            value = manager.get("test.yaml", "database.port")
            assert value == 5432

    def test_get_with_default(self):
        """Test getting non-existent key returns default"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            manager = ConfigManager(config_dir=config_dir)

            # Create test file
            test_config = {"name": "test"}
            config_file = config_dir / "test.yaml"
            with open(config_file, "w") as f:
                yaml.dump(test_config, f)

            # Get non-existent key
            value = manager.get("test.yaml", "nonexistent", default="default_value")
            assert value == "default_value"

    def test_set_simple_key(self):
        """Test setting simple configuration key"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            manager = ConfigManager(config_dir=config_dir)

            # Set value
            manager.set("test.yaml", "name", "new_value")

            # Verify
            value = manager.get("test.yaml", "name")
            assert value == "new_value"

    def test_set_nested_key(self):
        """Test setting nested configuration key"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            manager = ConfigManager(config_dir=config_dir)

            # Set nested value
            manager.set("test.yaml", "database.host", "localhost")
            manager.set("test.yaml", "database.port", 5432)

            # Verify
            host = manager.get("test.yaml", "database.host")
            port = manager.get("test.yaml", "database.port")
            assert host == "localhost"
            assert port == 5432

    def test_set_creates_nested_structure(self):
        """Test that set creates nested structure"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            manager = ConfigManager(config_dir=config_dir)

            # Set deeply nested value
            manager.set("test.yaml", "a.b.c.d", "value")

            # Verify structure
            value = manager.get("test.yaml", "a.b.c.d")
            assert value == "value"

    def test_clear_cache(self):
        """Test clearing configuration cache"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            manager = ConfigManager(config_dir=config_dir)

            # Create and load config
            test_config = {"value": 42}
            config_file = config_dir / "test.yaml"
            with open(config_file, "w") as f:
                yaml.dump(test_config, f)

            manager.load("test.yaml")
            assert "test.yaml" in manager._cache

            # Clear cache
            manager.clear_cache()
            assert len(manager._cache) == 0


class TestGlobalFunctions:
    """Tests for global convenience functions"""

    def test_load_config_with_custom_dir(self):
        """Test load_config with custom directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)

            # Create test file
            test_config = {"test": "value"}
            config_file = config_dir / "test.yaml"
            with open(config_file, "w") as f:
                yaml.dump(test_config, f)

            # Load config
            loaded = load_config("test.yaml", config_dir=config_dir)
            assert loaded == test_config

    def test_save_config_with_custom_dir(self):
        """Test save_config with custom directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)

            # Save config
            test_config = {"test": "value"}
            save_config("test.yaml", test_config, config_dir=config_dir)

            # Verify
            config_file = config_dir / "test.yaml"
            assert config_file.exists()

            with open(config_file) as f:
                loaded = yaml.safe_load(f)
                assert loaded == test_config
