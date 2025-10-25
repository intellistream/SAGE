"""
项目状态检查器单元测试
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from sage.tools.dev.tools.project_status_checker import ProjectStatusChecker


class TestProjectStatusChecker:
    """项目状态检查器测试"""

    @pytest.fixture
    def project_root(self):
        """获取项目根目录"""
        current = Path(__file__).parent
        while current.parent != current:
            if (current / "packages").exists() and (current / "pyproject.toml").exists():
                return str(current)
            current = current.parent
        # fallback到默认路径
        return str(Path(__file__).parent.parent.parent.parent.parent)

    def test_init(self, project_root):
        """测试初始化"""
        checker = ProjectStatusChecker(project_root)
        assert checker.project_root.is_absolute()
        assert (checker.project_root / "packages").exists()

    def test_check_environment(self, project_root):
        """测试环境检查"""
        checker = ProjectStatusChecker(project_root)
        env_info = checker._check_environment()

        assert "python_version" in env_info
        assert "python_executable" in env_info
        assert "working_directory" in env_info
        assert "environment_variables" in env_info

    def test_check_packages(self, project_root):
        """测试包检查"""
        checker = ProjectStatusChecker(project_root)
        packages_info = checker._check_packages()

        assert "packages_dir_exists" in packages_info
        assert "packages" in packages_info
        assert "summary" in packages_info

        if packages_info["packages_dir_exists"]:
            summary = packages_info["summary"]
            assert "total" in summary
            assert "installed" in summary
            assert "importable" in summary

    def test_check_dependencies(self, project_root):
        """测试依赖检查"""
        checker = ProjectStatusChecker(project_root)
        deps_info = checker._check_dependencies()

        assert "critical_packages" in deps_info
        assert "import_tests" in deps_info

        # 检查关键依赖
        critical = deps_info["critical_packages"]
        assert "typer" in critical
        assert "rich" in critical

    def test_check_all(self, project_root):
        """测试完整检查"""
        checker = ProjectStatusChecker(project_root)
        status_data = checker.check_all(verbose=False)

        assert "timestamp" in status_data
        assert "project_root" in status_data
        assert "checks" in status_data

        checks = status_data["checks"]
        expected_checks = [
            "environment",
            "packages",
            "dependencies",
            "services",
            "configuration",
        ]
        for check_name in expected_checks:
            assert check_name in checks
            assert "status" in checks[check_name]

    def test_generate_status_summary(self, project_root):
        """测试状态摘要生成"""
        checker = ProjectStatusChecker(project_root)
        status_data = checker.check_all(verbose=False)
        summary = checker.generate_status_summary(status_data)

        assert "SAGE 项目状态报告" in summary
        assert "检查时间" in summary
        assert "项目路径" in summary
        assert "检查项目" in summary


@pytest.mark.unit
class TestProjectStatusCheckerMocked:
    """使用Mock的项目状态检查器测试"""

    @patch("sage.tools.dev.tools.project_status_checker.subprocess.run")
    def test_check_ray_status_success(self, mock_run):
        """测试Ray状态检查成功"""
        mock_run.return_value = Mock(returncode=0, stdout="Ray cluster running")

        checker = ProjectStatusChecker(".")
        ray_status = checker._check_ray_status()

        assert ray_status["available"] is True
        assert ray_status["running"] is True
        assert "Ray cluster running" in ray_status["output"]

    @patch("sage.tools.dev.tools.project_status_checker.subprocess.run")
    def test_check_ray_status_not_running(self, mock_run):
        """测试Ray状态检查失败"""
        mock_run.return_value = Mock(returncode=1, stderr="Ray not running")

        checker = ProjectStatusChecker(".")
        ray_status = checker._check_ray_status()

        assert ray_status["available"] is True
        assert ray_status["running"] is False

    @patch("sage.tools.dev.tools.project_status_checker.subprocess.run")
    def test_check_ray_status_not_available(self, mock_run):
        """测试Ray命令不可用"""
        mock_run.side_effect = FileNotFoundError("Ray command not found")

        checker = ProjectStatusChecker(".")
        ray_status = checker._check_ray_status()

        assert ray_status["available"] is False
        assert "Ray command not found" in ray_status["error"]
