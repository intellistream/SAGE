
import socket, ray
import threading
import os
from pathlib import Path

def ensure_ray_initialized():
    """
    确保Ray已经初始化，如果未初始化则进行初始化。
    """
    if not ray.is_initialized():
        try:
            # 在测试环境中，先尝试连接现有的Ray集群
            ray.init(address="auto", ignore_reinit_error=True)
            print(f"Ray initialized with existing cluster")
        except Exception:
            try:
                # 如果连接失败，启动本地Ray实例
                ray.init(ignore_reinit_error=True)
                print(f"Ray initialized locally")
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
    try:
        import ray
        return ray.is_initialized()
    except ImportError:
        return False