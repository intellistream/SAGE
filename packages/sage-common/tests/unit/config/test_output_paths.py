"""Tests for SAGE output paths configuration module."""

import os
from unittest.mock import patch

from sage.common.config.output_paths import (
    SageOutputPaths,
    find_sage_project_root,
    get_appropriate_sage_dir,
    get_logs_dir,
    get_output_dir,
    get_sage_paths,
    get_temp_dir,
    initialize_sage_paths,
)


class TestFindSageProjectRoot:
    """Tests for find_sage_project_root function."""

    def test_find_from_sage_project(self, tmp_path):
        """测试从SAGE项目内部查找项目根目录"""
        # 创建SAGE项目结构
        project_root = tmp_path / "sage_project"
        project_root.mkdir()
        (project_root / "packages").mkdir()
        (project_root / "packages" / "sage-common").mkdir()

        # 从子目录查找
        subdir = project_root / "packages" / "sage-common" / "src"
        subdir.mkdir(parents=True)

        found_root = find_sage_project_root(subdir)
        assert found_root == project_root

    def test_find_from_packages_marker(self, tmp_path):
        """测试使用packages标记查找项目根目录"""
        project_root = tmp_path / "project"
        project_root.mkdir()
        (project_root / "packages").mkdir()
        (project_root / "packages" / "sage").mkdir(parents=True)

        found_root = find_sage_project_root(project_root / "packages")
        assert found_root == project_root

    def test_no_project_root_found(self, tmp_path):
        """测试在非项目目录中查找返回None"""
        non_project = tmp_path / "not_a_project"
        non_project.mkdir()

        found_root = find_sage_project_root(non_project)
        assert found_root is None


class TestGetAppropriateSageDir:
    """Tests for get_appropriate_sage_dir function."""

    def test_use_environment_variable(self, tmp_path, monkeypatch):
        """测试使用SAGE_OUTPUT_DIR环境变量"""
        sage_dir = tmp_path / "custom_sage"
        monkeypatch.setenv("SAGE_OUTPUT_DIR", str(sage_dir))

        result = get_appropriate_sage_dir()
        assert result == sage_dir
        assert sage_dir.exists()

    def test_use_explicit_project_root(self, tmp_path):
        """测试使用显式项目根目录"""
        project_root = tmp_path / "project"
        project_root.mkdir()

        result = get_appropriate_sage_dir(project_root)
        assert result == project_root / ".sage"
        assert result.exists()

    def test_auto_detect_development_environment(self, tmp_path, monkeypatch):
        """测试自动检测开发环境"""
        project_root = tmp_path / "sage_project"
        project_root.mkdir()
        (project_root / "packages").mkdir()
        (project_root / "packages" / "sage-common").mkdir(parents=True)

        monkeypatch.chdir(project_root)
        monkeypatch.delenv("SAGE_OUTPUT_DIR", raising=False)

        result = get_appropriate_sage_dir()
        assert result == project_root / ".sage"


class TestSageOutputPaths:
    """Tests for SageOutputPaths class."""

    def test_initialization_with_explicit_root(self, tmp_path):
        """测试使用显式根目录初始化"""
        project_root = tmp_path / "project"
        project_root.mkdir()

        paths = SageOutputPaths(project_root)

        assert paths.sage_dir == project_root / ".sage"
        assert paths.project_root == project_root
        assert paths.sage_dir.exists()

    def test_directory_properties(self, tmp_path):
        """测试目录属性"""
        project_root = tmp_path / "project"
        project_root.mkdir()

        paths = SageOutputPaths(project_root)

        # 测试所有目录属性
        assert paths.logs_dir == paths.sage_dir / "logs"
        assert paths.output_dir == paths.sage_dir / "output"
        assert paths.temp_dir == paths.sage_dir / "temp"
        assert paths.cache_dir == paths.sage_dir / "cache"
        assert paths.reports_dir == paths.sage_dir / "reports"
        assert paths.coverage_dir == paths.sage_dir / "coverage"
        assert paths.test_logs_dir == paths.sage_dir / "test_logs"
        assert paths.experiments_dir == paths.sage_dir / "experiments"
        assert paths.issues_dir == paths.sage_dir / "issues"
        assert paths.states_dir == paths.sage_dir / "states"
        assert paths.benchmarks_dir == paths.sage_dir / "benchmarks"
        assert paths.studio_dir == paths.sage_dir / "studio"

        # 验证所有目录已创建
        for dir_prop in [
            "logs_dir",
            "output_dir",
            "temp_dir",
            "cache_dir",
            "reports_dir",
            "coverage_dir",
            "test_logs_dir",
            "experiments_dir",
            "issues_dir",
            "states_dir",
            "benchmarks_dir",
            "studio_dir",
        ]:
            assert getattr(paths, dir_prop).exists()

    def test_get_log_file(self, tmp_path):
        """测试获取日志文件路径"""
        project_root = tmp_path / "project"
        project_root.mkdir()

        paths = SageOutputPaths(project_root)

        # 不带子目录
        log_file = paths.get_log_file("test.log")
        assert log_file == paths.logs_dir / "test.log"

        # 带子目录
        log_file_sub = paths.get_log_file("test.log", subdir="component")
        assert log_file_sub == paths.logs_dir / "component" / "test.log"
        assert log_file_sub.parent.exists()

    def test_get_output_file(self, tmp_path):
        """测试获取输出文件路径"""
        project_root = tmp_path / "project"
        project_root.mkdir()

        paths = SageOutputPaths(project_root)

        output_file = paths.get_output_file("result.json")
        assert output_file == paths.output_dir / "result.json"

        output_file_sub = paths.get_output_file("result.json", subdir="experiments")
        assert output_file_sub == paths.output_dir / "experiments" / "result.json"

    def test_get_temp_file(self, tmp_path):
        """测试获取临时文件路径"""
        project_root = tmp_path / "project"
        project_root.mkdir()

        paths = SageOutputPaths(project_root)

        temp_file = paths.get_temp_file("temp.dat")
        assert temp_file == paths.temp_dir / "temp.dat"

    def test_get_cache_file(self, tmp_path):
        """测试获取缓存文件路径"""
        project_root = tmp_path / "project"
        project_root.mkdir()

        paths = SageOutputPaths(project_root)

        cache_file = paths.get_cache_file("cache.db")
        assert cache_file == paths.cache_dir / "cache.db"

    def test_get_test_env_dir(self, tmp_path):
        """测试获取测试环境目录"""
        project_root = tmp_path / "project"
        project_root.mkdir()

        paths = SageOutputPaths(project_root)

        test_env = paths.get_test_env_dir("my_test")
        assert test_env == paths.temp_dir / "my_test"
        assert test_env.exists()

    def test_get_ray_temp_dir(self, tmp_path):
        """测试获取Ray临时目录"""
        project_root = tmp_path / "project"
        project_root.mkdir()

        paths = SageOutputPaths(project_root)

        ray_dir = paths.get_ray_temp_dir()
        assert ray_dir == paths.temp_dir / "ray"
        assert ray_dir.exists()

    def test_setup_environment_variables(self, tmp_path, monkeypatch):
        """测试设置环境变量"""
        project_root = tmp_path / "project"
        project_root.mkdir()

        paths = SageOutputPaths(project_root)
        env_vars = paths.setup_environment_variables()

        assert os.environ["SAGE_OUTPUT_DIR"] == str(paths.sage_dir)
        assert os.environ["SAGE_HOME"] == str(paths.sage_dir)
        assert os.environ["SAGE_LOGS_DIR"] == str(paths.logs_dir)
        assert os.environ["SAGE_TEMP_DIR"] == str(paths.temp_dir)
        assert os.environ["RAY_TMPDIR"] == str(paths.temp_dir / "ray")

        assert env_vars["sage_dir"] == paths.sage_dir
        assert env_vars["logs_dir"] == paths.logs_dir


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_get_logs_dir(self, tmp_path):
        """测试get_logs_dir便捷函数"""
        # Clear cache first
        get_sage_paths.cache_clear()

        with patch(
            "sage.common.config.output_paths.get_appropriate_sage_dir"
        ) as mock_get:
            mock_get.return_value = tmp_path / ".sage"
            (tmp_path / ".sage" / "logs").mkdir(parents=True)

            logs_dir = get_logs_dir(tmp_path)
            assert logs_dir.name == "logs"

    def test_get_output_dir(self, tmp_path):
        """测试get_output_dir便捷函数"""
        get_sage_paths.cache_clear()

        with patch(
            "sage.common.config.output_paths.get_appropriate_sage_dir"
        ) as mock_get:
            mock_get.return_value = tmp_path / ".sage"
            (tmp_path / ".sage" / "output").mkdir(parents=True)

            output_dir = get_output_dir(tmp_path)
            assert output_dir.name == "output"

    def test_get_temp_dir(self, tmp_path):
        """测试get_temp_dir便捷函数"""
        get_sage_paths.cache_clear()

        with patch(
            "sage.common.config.output_paths.get_appropriate_sage_dir"
        ) as mock_get:
            mock_get.return_value = tmp_path / ".sage"
            (tmp_path / ".sage" / "temp").mkdir(parents=True)

            temp_dir = get_temp_dir(tmp_path)
            assert temp_dir.name == "temp"

    def test_initialize_sage_paths(self, tmp_path, monkeypatch):
        """测试initialize_sage_paths函数"""
        get_sage_paths.cache_clear()
        project_root = tmp_path / "project"
        project_root.mkdir()

        paths = initialize_sage_paths(project_root)

        assert isinstance(paths, SageOutputPaths)
        assert paths.sage_dir.exists()
        # 验证环境变量已设置
        assert "SAGE_OUTPUT_DIR" in os.environ
