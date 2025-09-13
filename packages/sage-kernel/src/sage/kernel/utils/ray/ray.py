import os
import socket
import threading
from pathlib import Path

try:
    import ray

    RAY_AVAILABLE = True
except ImportError:
    ray = None
    RAY_AVAILABLE = False


def get_sage_kernel_runtime_env():
    """
    获取Sage内核的Ray运行环境配置，确保Actor可以访问sage模块
    """
    import os
    import sys

    # 动态获取sage-kernel源码路径
    current_file = os.path.abspath(__file__)
    # 从当前文件往上找到sage-kernel/src目录
    parts = current_file.split("/")
    try:
        kernel_idx = next(i for i, part in enumerate(parts) if part == "sage-kernel")
        sage_kernel_src = "/".join(parts[: kernel_idx + 1]) + "/src"
    except StopIteration:
        # 备用方法：从环境变量或当前工作目录推断
        cwd = os.getcwd()
        if "sage-kernel" in cwd:
            parts = cwd.split("/")
            kernel_idx = next(
                i for i, part in enumerate(parts) if part == "sage-kernel"
            )
            sage_kernel_src = "/".join(parts[: kernel_idx + 1]) + "/src"
        else:
            # 最后的备用方法
            sage_kernel_src = os.path.expanduser("~/SAGE/packages/sage-kernel/src")

    if not os.path.exists(sage_kernel_src):
        print(f"警告：无法找到sage-kernel源码路径: {sage_kernel_src}")
        return {}

    # 构建runtime_env配置
    runtime_env = {
        "py_modules": [sage_kernel_src],
        "env_vars": {
            "PYTHONPATH": sage_kernel_src + ":" + os.environ.get("PYTHONPATH", "")
        },
    }

    return runtime_env


def ensure_ray_initialized(runtime_env=None):
    """
    确保Ray已经初始化，如果没有则初始化Ray。

    Args:
        runtime_env: Ray运行环境配置，如果为None则使用默认的sage配置
    """
    if not RAY_AVAILABLE:
        raise ImportError("Ray is not available")

    if not ray.is_initialized():
        try:
            # 使用标准模式但限制资源，支持async actors和队列
            # 设置较少的CPU数量避免过度资源消耗
            ray.init(
                ignore_reinit_error=True, 
                num_cpus=2,  # 限制CPU使用
                num_gpus=0,  # 不使用GPU
                object_store_memory=200000000,  # 200MB object store
                log_to_driver=False  # 减少日志输出
            )
            print(f"Ray initialized in standard mode with limited resources")
        except Exception as e:
            print(f"Failed to initialize Ray: {e}")
            raise
    else:
        print("Ray is already initialized.")


def is_distributed_environment() -> bool:
    """
    检查是否在分布式环境中运行。
    尝试导入Ray并检查是否已初始化。
    """
    if not RAY_AVAILABLE:
        return False

    try:
        return ray.is_initialized()
    except Exception:
        return False
