from sage.common.utils.logging.custom_logger import CustomLogger
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

try:
    from sage.common.config.output_paths import get_sage_paths

    SAGE_OUTPUT_PATHS_AVAILABLE = True
except ImportError:
    SAGE_OUTPUT_PATHS_AVAILABLE = False


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
        self.logger.info(f"警告：无法找到sage-kernel源码路径: {sage_kernel_src}")
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
            # 准备初始化参数
            init_kwargs = {
                "ignore_reinit_error": True,
                "num_cpus": 2,  # 限制CPU使用
                "num_gpus": 0,  # 不使用GPU
                "object_store_memory": 200000000,  # 200MB object store
                "log_to_driver": False,  # 减少日志输出
                "include_dashboard": False,  # 禁用dashboard减少资源占用
            }

            # 设置Ray临时目录到SAGE的temp目录
            ray_temp_dir = None

            # 使用统一的output_paths系统
            if SAGE_OUTPUT_PATHS_AVAILABLE:
                try:
                    sage_paths = get_sage_paths()
                    # 设置环境变量
                    sage_paths.setup_environment_variables()
                    ray_temp_dir = sage_paths.get_ray_temp_dir()
                    init_kwargs["_temp_dir"] = str(ray_temp_dir)
                    self.logger.info(f"Ray will use SAGE temp directory: {ray_temp_dir}")
                except Exception as e:
                    self.logger.info(
                        f"Warning: Failed to set Ray temp directory via output_paths: {e}"
                    )

                    # 如果没有成功设置，使用默认行为
                    init_kwargs["_temp_dir"] = str(ray_temp_dir)
                    self.logger.info(
                        f"Ray will use SAGE temp directory (fallback): {ray_temp_dir}"
                    )
                except Exception as e:
                    self.logger.info(
                        f"Warning: Failed to set Ray temp directory via fallback: {e}"
                    )

            if ray_temp_dir is None:
                self.logger.info("SAGE paths not available, Ray will use default temp directory")

            # 如果提供了runtime_env，使用它；否则使用默认的sage配置
            if runtime_env is not None:
                init_kwargs["runtime_env"] = runtime_env
            else:
                # 使用默认的sage配置
                sage_runtime_env = get_sage_kernel_runtime_env()
                if sage_runtime_env:
                    init_kwargs["runtime_env"] = sage_runtime_env

            # 使用标准模式但限制资源，支持async actors和队列
            ray.init(**init_kwargs)
            self.logger.info(f"Ray initialized in standard mode with limited resources")
        except Exception as e:
            self.logger.info(f"Failed to initialize Ray: {e}")
            raise
    else:
        self.logger.info("Ray is already initialized.")


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
