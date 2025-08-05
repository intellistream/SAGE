"""
JobManager 测试配置和运行器
提供统一的测试配置、标记和运行入口
"""
import pytest
import sys
import os
from pathlib import Path

# 添加项目根路径到Python路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

# 测试标记配置
pytest_plugins = []

def pytest_configure(config):
    """配置pytest标记"""
    config.addinivalue_line(
        "markers", "unit: 单元测试 - 测试单个组件或函数"
    )
    config.addinivalue_line(
        "markers", "integration: 集成测试 - 测试组件间集成"
    )
    config.addinivalue_line(
        "markers", "slow: 慢速测试 - 运行时间较长的测试"
    )
    config.addinivalue_line(
        "markers", "external: 外部依赖测试 - 需要外部服务的测试"
    )
    config.addinivalue_line(
        "markers", "performance: 性能测试 - 测试性能指标"
    )


def pytest_collection_modifyitems(config, items):
    """修改测试收集，添加默认标记"""
    for item in items:
        # 如果测试没有任何标记，添加unit标记
        if not any(item.iter_markers()):
            item.add_marker(pytest.mark.unit)
        
        # 为慢速测试添加超时
        if item.get_closest_marker("slow"):
            item.add_marker(pytest.mark.timeout(300))  # 5分钟超时


def run_unit_tests():
    """运行单元测试"""
    return pytest.main([
        "-v",
        "-m", "unit",
        "--tb=short",
        "--strict-markers",
        str(Path(__file__).parent)
    ])


def run_integration_tests():
    """运行集成测试"""
    return pytest.main([
        "-v", 
        "-m", "integration",
        "--tb=short",
        "--strict-markers",
        str(Path(__file__).parent)
    ])


def run_all_tests():
    """运行所有测试"""
    return pytest.main([
        "-v",
        "--tb=short", 
        "--strict-markers",
        str(Path(__file__).parent)
    ])


def run_performance_tests():
    """运行性能测试"""
    return pytest.main([
        "-v",
        "-m", "performance or slow",
        "--tb=short",
        "--strict-markers", 
        str(Path(__file__).parent)
    ])


def run_quick_tests():
    """运行快速测试（排除慢速测试）"""
    return pytest.main([
        "-v",
        "-m", "not slow and not external",
        "--tb=short",
        "--strict-markers",
        str(Path(__file__).parent)
    ])


def run_coverage_tests():
    """运行带覆盖率的测试"""
    try:
        import pytest_cov
    except ImportError:
        print("需要安装 pytest-cov: pip install pytest-cov")
        return 1
    
    return pytest.main([
        "-v",
        "--cov=sage.jobmanager",
        "--cov-report=html:htmlcov",
        "--cov-report=term",
        "--cov-report=xml",
        "--cov-fail-under=80",
        "--tb=short",
        "--strict-markers",
        str(Path(__file__).parent)
    ])


def run_specific_test(test_pattern):
    """运行特定模式的测试"""
    return pytest.main([
        "-v",
        "-k", test_pattern,
        "--tb=short",
        "--strict-markers",
        str(Path(__file__).parent)
    ])


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="JobManager测试运行器")
    parser.add_argument(
        "test_type",
        choices=["unit", "integration", "all", "performance", "quick", "coverage"],
        help="要运行的测试类型"
    )
    parser.add_argument(
        "-k", "--keyword",
        help="测试关键字过滤"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="详细输出"
    )
    
    args = parser.parse_args()
    
    if args.keyword:
        exit_code = run_specific_test(args.keyword)
    elif args.test_type == "unit":
        exit_code = run_unit_tests()
    elif args.test_type == "integration":
        exit_code = run_integration_tests()
    elif args.test_type == "all":
        exit_code = run_all_tests()
    elif args.test_type == "performance":
        exit_code = run_performance_tests()
    elif args.test_type == "quick":
        exit_code = run_quick_tests()
    elif args.test_type == "coverage":
        exit_code = run_coverage_tests()
    else:
        print(f"未知的测试类型: {args.test_type}")
        exit_code = 1
    
    sys.exit(exit_code)
