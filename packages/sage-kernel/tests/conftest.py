"""
sage-kernel测试配置

设置正确的Python路径和共享的测试fixtures
"""

import os
import sys
from pathlib import Path

import pytest

# 获取项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
SRC_DIR = PROJECT_ROOT / "src"
PACKAGES_DIR = PROJECT_ROOT.parent

# 需要添加的依赖包路径
DEPENDENCY_PACKAGES = [
    "sage-common",
    "sage-platform",
    "sage-libs",
    "sage-middleware",
]

# 添加 sage-kernel 源码路径
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# 添加所有依赖包的源码路径
for pkg_name in DEPENDENCY_PACKAGES:
    pkg_src_dir = PACKAGES_DIR / pkg_name / "src"
    if pkg_src_dir.exists() and str(pkg_src_dir) not in sys.path:
        sys.path.insert(0, str(pkg_src_dir))

# 设置环境变量
os.environ.setdefault("SAGE_TEST_MODE", "1")
os.environ.setdefault("SAGE_LOG_LEVEL", "INFO")


@pytest.fixture
def sage_test_env_config():
    """统一的SAGE测试环境配置

    返回标准化的测试环境配置，确保所有测试使用.sage目录
    而不是在项目根目录创建test_env目录
    """
    from sage.common.config.output_paths import get_sage_paths, get_test_env_dir

    # 使用统一的路径管理
    sage_paths = get_sage_paths()
    test_env_dir = get_test_env_dir("test_env")

    return {
        "name": "test_env",
        "platform": "local",
        "env_base_dir": str(test_env_dir),
        "console_log_level": "INFO",
        "project_root": str(sage_paths.project_root),
        "sage_dir": str(sage_paths.sage_dir),
    }


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """自动设置测试环境"""
    # 验证关键模块可以导入
    try:
        import importlib
        import types

        # Import modules dynamically to avoid static analysis issues with namespace packages
        sage_common: types.ModuleType = importlib.import_module("sage.common")
        sage_kernel: types.ModuleType = importlib.import_module("sage.kernel")

        print("✓ 测试环境设置成功")
        print(f"✓ sage.kernel: {sage_kernel.__path__}")
        # sage.common is a namespace package, check __path__ dynamically
        if hasattr(sage_common, "__path__"):
            print(f"✓ sage.common: {sage_common.__path__}")
        else:
            print("✓ sage.common: module loaded successfully")
    except ImportError as e:
        print(f"❌ 测试环境设置失败: {e}")
        raise

    yield

    # 清理（无需 Ray shutdown）
    pass
