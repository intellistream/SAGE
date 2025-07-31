
import socket, ray
import threading
import os
from pathlib import Path

def ensure_ray_initialized():
    """
    确保Ray已经初始化，如果未初始化则进行初始化。
    """
    if not ray.is_initialized():
        # # 获取当前脚本所在目录
        # project_root = Path(__file__).parent.parent
        # ray_logs_dir = project_root / "logs" / "ray"

        # # 确保日志目录存在
        # os.makedirs(ray_logs_dir, exist_ok=True)
        
        # 初始化Ray
        ray.init(address="auto")
        print(f"Ray initialized with logs in /var/lib/ray_shared")
    else:
        print("Ray is already initialized.")

def is_distributed_environment() -> bool:
    """
    检查是否在分布式环境中运行。
    尝试导入Ray并检查是否已初始化。
    """
    try:
        import ray
        return ray.is_initialized()
    except ImportError:
        return False