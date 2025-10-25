"""
Tests for sage.common.utils.config.loader module
==================================

单元测试配置加载器模块的功能，包括：
- 配置文件查找逻辑
- 多种配置源的优先级
- 错误处理和异常情况
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from sage.common.utils.config.loader import load_config


@pytest.mark.unit
class TestLoadConfig:
    """配置加载器测试类"""

    def setup_method(self):
        """测试前准备"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.config_dir = self.temp_dir / "config"
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # 创建测试配置文件
        self.test_config = {
            "database": {"host": "localhost", "port": 5432, "name": "test_db"},
            "logging": {"level": "INFO", "handlers": ["console", "file"]},
            "features": {"cache_enabled": True, "max_connections": 100},
        }

        self.config_file = self.config_dir / "config.yaml"
        with open(self.config_file, "w") as f:
            yaml.dump(self.test_config, f)

    def teardown_method(self):
        """测试后清理"""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @pytest.mark.unit
    def test_load_config_with_explicit_absolute_path(self):
        """测试显式绝对路径加载配置"""
        config = load_config(str(self.config_file))
        assert config == self.test_config
        assert config["database"]["host"] == "localhost"
        assert config["logging"]["level"] == "INFO"

    @pytest.mark.unit
    def test_load_config_with_relative_path(self):
        """测试相对路径加载配置"""
        with patch("inspect.currentframe") as mock_frame:
            # 模拟调用者文件路径
            mock_caller_frame = MagicMock()
            mock_caller_frame.f_globals = {"__file__": str(self.temp_dir / "caller.py")}
            mock_frame.return_value.f_back = mock_caller_frame

            config = load_config("config/config.yaml")
            assert config == self.test_config

    @pytest.mark.unit
    def test_load_config_with_bare_filename(self):
        """测试单纯文件名加载配置"""
        with patch("inspect.currentframe") as mock_frame:
            mock_caller_frame = MagicMock()
            mock_caller_frame.f_globals = {"__file__": str(self.temp_dir / "caller.py")}
            mock_frame.return_value.f_back = mock_caller_frame

            config = load_config("config.yaml")
            assert config == self.test_config

    @pytest.mark.unit
    def test_load_config_with_env_override(self):
        """测试环境变量覆盖配置路径"""
        env_config_file = self.temp_dir / "env_config.yaml"
        env_config = {"env": "development", "debug": True}

        with open(env_config_file, "w") as f:
            yaml.dump(env_config, f)

        with patch.dict(os.environ, {"SAGE_CONFIG": str(env_config_file)}):
            config = load_config()
            assert config == env_config

    @pytest.mark.unit
    def test_load_config_priority_order(self):
        """测试配置文件优先级顺序"""
        # 创建多个配置文件
        explicit_config = self.temp_dir / "explicit.yaml"
        with open(explicit_config, "w") as f:
            yaml.dump({"source": "explicit"}, f)

        env_config = self.temp_dir / "env.yaml"
        with open(env_config, "w") as f:
            yaml.dump({"source": "env"}, f)

        # 测试显式路径优先级最高
        with patch.dict(os.environ, {"SAGE_CONFIG": str(env_config)}):
            config = load_config(str(explicit_config))
            assert config["source"] == "explicit"

    @pytest.mark.unit
    def test_load_config_user_and_system_fallback(self):
        """测试用户级和系统级配置文件回退"""
        with patch("inspect.currentframe") as mock_frame, patch(
            "sage.common.utils.config.loader.user_config_dir"
        ) as mock_user_dir, patch(
            "sage.common.utils.config.loader.site_config_dir"
        ) as mock_site_dir:

            # 模拟调用者文件路径
            mock_caller_frame = MagicMock()
            mock_caller_frame.f_globals = {"__file__": str(self.temp_dir / "caller.py")}
            mock_frame.return_value.f_back = mock_caller_frame

            # 设置用户和系统配置目录
            user_config_dir = Path(self.temp_dir) / "user_config"
            system_config_dir = Path(self.temp_dir) / "system_config"
            user_config_dir.mkdir(exist_ok=True)
            system_config_dir.mkdir(exist_ok=True)

            mock_user_dir.return_value = str(user_config_dir)
            mock_site_dir.return_value = str(system_config_dir)

            # 创建用户级配置文件
            user_config_file = user_config_dir / "config.yaml"
            user_config = {"source": "user"}
            with open(user_config_file, "w") as f:
                yaml.dump(user_config, f)

            # 删除项目级配置文件，强制使用用户级
            self.config_file.unlink()

            config = load_config()
            assert config["source"] == "user"

    @pytest.mark.unit
    def test_load_config_file_not_found_error(self):
        """测试配置文件未找到时的错误处理"""
        with patch("inspect.currentframe") as mock_frame:
            mock_caller_frame = MagicMock()
            mock_caller_frame.f_globals = {"__file__": str(self.temp_dir / "caller.py")}
            mock_frame.return_value.f_back = mock_caller_frame

            # 删除所有配置文件
            self.config_file.unlink()

            with pytest.raises(FileNotFoundError) as exc_info:
                load_config()

            assert "No config found" in str(exc_info.value)
            assert "Checked:" in str(exc_info.value)

    @pytest.mark.unit
    def test_load_config_invalid_yaml(self):
        """测试无效YAML文件的错误处理"""
        invalid_config_file = self.config_dir / "invalid.yaml"
        with open(invalid_config_file, "w") as f:
            f.write("invalid: yaml: content: [")

        with pytest.raises(yaml.YAMLError):
            load_config(str(invalid_config_file))

    @pytest.mark.unit
    def test_load_config_empty_file(self):
        """测试空配置文件处理"""
        empty_config_file = self.config_dir / "empty.yaml"
        empty_config_file.touch()

        config = load_config(str(empty_config_file))
        assert config is None

    @pytest.mark.unit
    def test_load_config_project_root_detection(self):
        """测试项目根目录检测逻辑"""
        # 创建项目结构
        project_root = Path(self.temp_dir) / "project"
        project_root.mkdir()

        # 创建项目标识文件
        (project_root / "pyproject.toml").touch()
        (project_root / "config").mkdir()

        config_file = project_root / "config" / "config.yaml"
        with open(config_file, "w") as f:
            yaml.dump({"project": "detected"}, f)

        # 从子目录调用
        subdir = project_root / "src" / "app"
        subdir.mkdir(parents=True)
        caller_file = subdir / "main.py"
        caller_file.touch()

        with patch("inspect.currentframe") as mock_frame:
            mock_caller_frame = MagicMock()
            mock_caller_frame.f_globals = {"__file__": str(caller_file)}
            mock_frame.return_value.f_back = mock_caller_frame

            config = load_config()
            assert config["project"] == "detected"

    @pytest.mark.unit
    def test_load_config_no_caller_frame(self):
        """测试无法获取调用者信息时的回退逻辑"""
        with patch("inspect.currentframe") as mock_frame:
            mock_frame.return_value.f_back.f_globals = {}

            with patch("pathlib.Path.cwd") as mock_cwd:
                mock_cwd.return_value = Path(self.temp_dir)
                config = load_config()
                assert config == self.test_config


@pytest.mark.integration
class TestLoadConfigIntegration:
    """配置加载器集成测试"""

    @pytest.mark.integration
    def test_load_config_with_real_project_structure(self):
        """测试真实项目结构中的配置加载"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建真实的项目结构
            project_dir = Path(temp_dir) / "sage_project"
            config_dir = project_dir / "config"
            src_dir = project_dir / "src" / "sage"

            project_dir.mkdir()
            config_dir.mkdir(parents=True)
            src_dir.mkdir(parents=True)

            # 创建项目标识文件
            (project_dir / "pyproject.toml").write_text("[build-system]")

            # 创建配置文件
            config_content = {
                "app_name": "SAGE",
                "version": "1.0.0",
                "database": {"url": "postgresql://localhost/sage"},
            }

            config_file = config_dir / "config.yaml"
            with open(config_file, "w") as f:
                yaml.dump(config_content, f)

            # 从源码目录中的模拟文件加载配置
            with patch("inspect.currentframe") as mock_frame:
                mock_caller_frame = MagicMock()
                mock_caller_frame.f_globals = {"__file__": str(src_dir / "app.py")}
                mock_frame.return_value.f_back = mock_caller_frame

                config = load_config()
                assert config["app_name"] == "SAGE"
                assert config["database"]["url"] == "postgresql://localhost/sage"


# Fixtures for testing
@pytest.fixture
def temp_config_dir():
    """提供临时配置目录的fixture"""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_dir = Path(temp_dir) / "config"
        config_dir.mkdir()
        yield config_dir


@pytest.fixture
def sample_config():
    """提供示例配置的fixture"""
    return {
        "app": {"name": "test_app", "version": "1.0.0"},
        "database": {"host": "localhost", "port": 5432},
    }


@pytest.mark.unit
def test_load_config_with_fixtures(temp_config_dir, sample_config):
    """使用fixtures的测试示例"""
    config_file = temp_config_dir / "config.yaml"
    with open(config_file, "w") as f:
        yaml.dump(sample_config, f)

    with patch("inspect.currentframe") as mock_frame:
        mock_caller_frame = MagicMock()
        mock_caller_frame.f_globals = {"__file__": str(temp_config_dir.parent / "app.py")}
        mock_frame.return_value.f_back = mock_caller_frame

        config = load_config()
        assert config == sample_config
