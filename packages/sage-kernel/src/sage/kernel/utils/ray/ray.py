
import socket
import threading
import os
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
    parts = current_file.split('/')
    try:
        kernel_idx = next(i for i, part in enumerate(parts) if part == 'sage-kernel')
        sage_kernel_src = '/'.join(parts[:kernel_idx + 1]) + '/src'
    except StopIteration:
        # 备用方法：从环境变量或当前工作目录推断
        cwd = os.getcwd()
        if 'sage-kernel' in cwd:
            parts = cwd.split('/')
            kernel_idx = next(i for i, part in enumerate(parts) if part == 'sage-kernel')
            sage_kernel_src = '/'.join(parts[:kernel_idx + 1]) + '/src'
        else:
            # 最后的备用方法
            sage_kernel_src = os.path.expanduser('~/SAGE/packages/sage-kernel/src')
    
    if not os.path.exists(sage_kernel_src):
        print(f"警告：无法找到sage-kernel源码路径: {sage_kernel_src}")
        return {}
    
    # 构建runtime_env配置
    runtime_env = {
        "py_modules": [sage_kernel_src],
        "env_vars": {
            "PYTHONPATH": sage_kernel_src + ':' + os.environ.get('PYTHONPATH', '')
        }
    }
    
    return runtime_env

def ensure_ray_initialized(runtime_env=None):
    """
    确保Ray已经初始化，如果未初始化则进行初始化。
    
    Args:
        runtime_env: Ray运行环境配置，如果为None则使用默认的sage配置
    """
    if not RAY_AVAILABLE:
        raise ImportError("Ray is not available")
    
    if not ray.is_initialized():
        # 如果没有提供runtime_env，使用默认的sage配置
        if runtime_env is None:
            runtime_env = get_sage_kernel_runtime_env()
        
        try:
            # 直接启动本地Ray实例，避免连接超时问题
            ray.init(ignore_reinit_error=True, runtime_env=runtime_env)
            print(f"Ray initialized locally with runtime_env")
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