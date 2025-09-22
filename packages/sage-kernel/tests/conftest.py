"""
sage-kernel测试配置

设置正确的Python路径和共享的测试fixtures
"""

import os
import sys
from pathlib import Path

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
    import ray

    if not ray.is_initialized():
        # 尝试更宽松的Ray配置 - 使用最小允许内存
        ray.init(
            ignore_reinit_error=True,
            local_mode=True,
            object_store_memory=80000000,  # 80MB (最小允许值)
            num_cpus=1,
        )
except (ImportError, ValueError, RuntimeError) as e:
    # Ray不是必需的，或者内存不足时跳过
    print(f"⚠️ Ray初始化跳过: {e}")
    pass

import pytest


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """自动设置测试环境"""
    # 验证关键模块可以导入
    try:
        import sage.common
        import sage.core
        import sage.kernel

        print(f"✓ 测试环境设置成功")
        print(f"✓ sage.kernel: {sage.kernel.__path__}")
        print(f"✓ sage.core: {sage.core.__path__}")
        print(f"✓ sage.common: {sage.common.__path__}")
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
