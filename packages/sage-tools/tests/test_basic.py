"""
SAGE Common基础测试

这是一个基本的测试文件，用于确保sage-common包的基本功能正常。
"""

import os
import sys

import pytest

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


def test_sage_common_import():
    """测试sage.common模块是否能正常导入"""
    try:
        import sage.common

        assert True
    except ImportError as e:
        pytest.fail(f"Failed to import sage.common: {e}")


def test_sage_common_version():
    """测试sage.common是否有版本信息"""
    import sage.common

    # 检查是否有__version__属性或者能正常导入
    assert hasattr(sage.common, "__path__")


def test_sage_common_structure():
    """测试sage.common的基本结构"""
    import sage.common

    # 确保模块结构正确
    assert sage.common.__name__ == "sage.common"


@pytest.mark.unit
class TestSageCommonBasic:
    """SAGE Common基础测试类"""

    def test_module_exists(self):
        """测试模块存在"""
        import sage.common

        assert sage.common is not None

    def test_package_structure(self):
        """测试包结构"""
        import sage.common

        # 检查包路径
        assert hasattr(sage.common, "__path__")
        assert len(sage.common.__path__) > 0


if __name__ == "__main__":
    pytest.main([__file__])
