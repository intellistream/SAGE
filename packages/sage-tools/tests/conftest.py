"""
pytest配置文件
"""

import sys
from pathlib import Path

import pytest

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture
def project_root_path():
    """项目根目录路径"""
    return project_root


@pytest.fixture
def sage_tools_path():
    """sage-tools包路径"""
    return Path(__file__).parent.parent


@pytest.fixture
def test_data_dir():
    """测试数据目录"""
    return Path(__file__).parent / "data"


# 配置pytest标记
def pytest_configure(config):
    """配置pytest"""
    config.addinivalue_line("markers", "unit: 单元测试")
    config.addinivalue_line("markers", "integration: 集成测试")
    config.addinivalue_line("markers", "cli: CLI测试")
    config.addinivalue_line("markers", "slow: 慢速测试")
    config.addinivalue_line("markers", "quick: 快速测试")


def pytest_collection_modifyitems(config, items):
    """修改测试收集项"""
    # 为CLI相关的测试文件自动添加cli标记
    for item in items:
        if "cli" in str(item.fspath):
            item.add_marker(pytest.mark.cli)
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
            item.add_marker(pytest.mark.slow)
