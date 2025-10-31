"""
依赖分析器单元测试
"""

from pathlib import Path

import pytest

from sage.tools.dev.tools.dependency_analyzer import DependencyAnalyzer


@pytest.fixture
def project_root():
    """获取项目根目录的fixture"""
    current = Path(__file__).parent
    # 从 test_dev/ 向上找到项目根目录
    while current.parent != current:
        if (current / "packages").exists() and (current / "pyproject.toml").exists():
            return current
        current = current.parent
    # 如果找不到，使用相对路径估计 - 需要向上5级才能到达SAGE根目录
    return Path(__file__).parent.parent.parent.parent.parent


@pytest.mark.unit
class TestDependencyAnalyzer:
    """依赖分析器测试"""

    def test_init(self, project_root):
        """测试初始化"""
        analyzer = DependencyAnalyzer(str(project_root))
        assert analyzer.project_root.is_absolute()
        assert analyzer.packages_dir.exists()

    def test_analyze_all_dependencies(self, project_root):
        """测试分析所有依赖"""
        analyzer = DependencyAnalyzer(str(project_root))
        result = analyzer.analyze_all_dependencies()

        assert "project_root" in result
        assert "packages" in result
        assert "summary" in result
        assert "dependency_graph" in result

        summary = result["summary"]
        assert "total_packages" in summary
        assert "total_dependencies" in summary

    def test_check_dependency_health(self, project_root):
        """测试依赖健康检查"""
        analyzer = DependencyAnalyzer(str(project_root))
        result = analyzer.check_dependency_health()

        assert "health_score" in result
        assert "grade" in result
        assert "issues" in result
        assert "recommendations" in result

    def test_generate_dependency_report(self, project_root):
        """测试生成依赖报告"""
        analyzer = DependencyAnalyzer(str(project_root))
        result = analyzer.generate_dependency_report()

        assert isinstance(result, dict)
        # 报告应该包含分析结果
        assert len(result) > 0

    def test_find_package_directories(self, project_root):
        """测试查找包目录"""
        analyzer = DependencyAnalyzer(str(project_root))
        packages = analyzer._find_package_directories()

        assert isinstance(packages, list)
        # 应该找到一些包
        assert len(packages) > 0

        # 每个包都应该是目录
        for pkg in packages:
            assert pkg.is_dir()

    def test_is_python_package(self, project_root):
        """测试Python包识别"""
        analyzer = DependencyAnalyzer(str(project_root))

        # 测试真实的包目录
        packages_dir = analyzer.packages_dir
        if packages_dir.exists():
            for pkg_dir in packages_dir.iterdir():
                if pkg_dir.is_dir() and pkg_dir.name.startswith("sage-"):
                    assert analyzer._is_python_package(pkg_dir) is True

    def test_parse_dependency_spec(self, project_root):
        """测试依赖规格解析"""
        analyzer = DependencyAnalyzer(str(project_root))

        # 测试简单包名
        name, info = analyzer._parse_dependency_spec("requests")
        assert name == "requests"
        assert isinstance(info, dict)
        assert info["spec"] == "requests"

        # 测试带版本的包名
        name, info = analyzer._parse_dependency_spec("requests>=2.25.0")
        assert name == "requests"
        assert isinstance(info, dict)
        assert "requests" in info["spec"]

        # 测试复杂版本规格
        name, info = analyzer._parse_dependency_spec("numpy>=1.20.0,<2.0.0")
        assert name == "numpy"
        assert isinstance(info, dict)
        assert "numpy" in info["spec"]
