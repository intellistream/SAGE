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
COMMON_SRC_DIR = PROJECT_ROOT.parent / "sage-common" / "src"

# 添加到Python路径
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

if str(COMMON_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(COMMON_SRC_DIR))

# 设置环境变量
os.environ.setdefault("SAGE_TEST_MODE", "1")
os.environ.setdefault("SAGE_LOG_LEVEL", "INFO")

# 确保Ray在测试环境中正确初始化（如果需要且有足够内存）
try:
    # ray may be optional in test environments; import locally after path setup
    import ray

    from sage.common.config.output_paths import get_sage_paths

    if not ray.is_initialized():
        # 获取SAGE路径和设置环境
        sage_paths = get_sage_paths()
        sage_paths.setup_environment_variables()

        # 获取Ray临时目录
        ray_temp_dir = sage_paths.get_ray_temp_dir()

        # 尝试更宽松的Ray配置 - 使用最小允许内存
        ray.init(
            ignore_reinit_error=True,
            local_mode=True,
            object_store_memory=80000000,  # 80MB (最小允许值)
            num_cpus=1,
            _temp_dir=str(ray_temp_dir),  # 使用SAGE的temp目录
        )
        print(f"Ray initialized for tests with temp dir: {ray_temp_dir}")
except (ImportError, ValueError, RuntimeError) as e:
    # Ray不是必需的，或者内存不足时跳过
    print(f"⚠️ Ray初始化跳过: {e}")
    pass


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
        import sage.common
        import sage.kernel

        print("✓ 测试环境设置成功")
        print(f"✓ sage.kernel: {sage.kernel.__path__}")
        # Check if __path__ attribute exists before accessing it
        if hasattr(sage.common, "__path__"):
            print(f"✓ sage.common: {sage.common.__path__}")
        else:
            print("✓ sage.common: module loaded successfully")
    except ImportError as e:
        print(f"❌ 测试环境设置失败: {e}")
        raise

    yield

    # 清理
    try:
        import ray

        if ray.is_initialized():
            ray.shutdown()
    except ImportError:
        pass
