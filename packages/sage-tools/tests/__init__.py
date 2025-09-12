"""
SAGE Tools 测试包初始化
"""

# 测试配置
import os
import sys
from pathlib import Path

# 确保sage.tools模块可以被导入
test_dir = Path(__file__).parent
project_root = test_dir.parent.parent.parent
sys.path.insert(0, str(project_root))

# 测试标记
import pytest

# 定义测试标记
pytest_marks = {
    "unit": "单元测试标记",
    "integration": "集成测试标记", 
    "cli": "CLI测试标记",
    "slow": "慢速测试标记",
    "quick": "快速测试标记",
}

def pytest_configure(config):
    """配置pytest标记"""
    for mark, description in pytest_marks.items():
        config.addinivalue_line(
            "markers", f"{mark}: {description}"
        )
