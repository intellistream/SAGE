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

        # 使用非 local_mode 以避免测试间的资源竞争
        # local_mode=True 会导致所有 Ray 调用在同一进程中运行，容易超时
        ray.init(
            ignore_reinit_error=True,
            num_cpus=2,  # 至少2个CPU以支持并发
            object_store_memory=150 * 1024 * 1024,  # 150MB
            _temp_dir=str(ray_temp_dir),  # 使用SAGE的temp目录
            logging_level="ERROR",  # 减少日志输出
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
        print(f"✓ sage.common: {sage.common.__path__}")
    except ImportError as e:
        print(f"❌ 测试环境设置失败: {e}")
        raise

    yield

    # 清理 - 确保所有 Ray 资源都被释放
    try:
        import ray

        if ray.is_initialized():
            print("🧹 清理 Ray 资源...")
            ray.shutdown()
            print("✓ Ray 已关闭")
    except ImportError:
        pass
    except Exception as e:
        print(f"⚠️ Ray 清理警告: {e}")


@pytest.fixture
def ray_context():
    """为单个测试提供独立的 Ray 上下文
    
    用于需要 Ray 但又可能与其他测试冲突的场景
    """
    import ray
    
    # 如果 Ray 已初始化，记录状态
    was_initialized = ray.is_initialized()
    
    yield
    
    # 测试后不关闭全局 Ray，避免影响其他测试
    # 但如果测试创建了新的 Ray 对象，确保它们被清理
    pass


@pytest.fixture(scope="function")
def isolated_ray_context():
    """为测试提供完全隔离的 Ray 环境
    
    每个测试都会获得一个干净的 Ray 环境，测试后自动清理
    注意：这会关闭全局 Ray，不要与其他使用全局 Ray 的测试混用
    """
    import ray
    
    # 关闭现有的 Ray（如果有）
    if ray.is_initialized():
        ray.shutdown()
    
    yield
    
    # 测试后关闭 Ray
    if ray.is_initialized():
        ray.shutdown()
