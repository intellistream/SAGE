import threading
from typing import Dict, Any
from sage_runtime.base_runtime import BaseRuntime
from sage_runtime.runtimes.local_runtime import  LocalRuntime
from sage_runtime.runtimes.ray_runtime import RayRuntime
from sage_utils.custom_logger import CustomLogger

class RuntimeManager:
    """
    运行时管理器，负责管理不同平台的运行时实例
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __init__(self, session_folder: str = None):
        # 确保只初始化一次
        if hasattr(self, "_initialized"):
            return
        self._initialized = True
        
        self.backends: Dict[str, Any] = {}
        self.session_folder = CustomLogger.get_session_folder()
        self.logger = CustomLogger(
            filename=f"RuntimeManager",
            session_folder=session_folder,
            console_output="WARNING",
            file_output="DEBUG",
            global_output = "WARNING",
        )
    
    def __new__(cls):
        # 禁止直接实例化
        raise RuntimeError("请通过 get_instance() 方法获取实例")
    
    @classmethod
    def get_instance(cls):
        """获取RuntimeManager的唯一实例"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    # 绕过 __new__ 的异常，直接创建实例
                    instance = super().__new__(cls)
                    instance.__init__()
                    cls._instance = instance
        return cls._instance
    
    @classmethod
    def reset_instance(cls):
        """重置实例（主要用于测试）"""
        with cls._lock:
            if cls._instance:
                cls._instance.shutdown_all()
                cls._instance = None
    
    def get(self, platform: str,*args, **kwargs) -> BaseRuntime:
        """
        获取指定平台的运行时实例，支持延迟初始化
        
        Args:
            platform: 平台名称 ("remote", "local")
            **kwargs: 运行时初始化参数
            
        Returns:
            运行时实例
        """
        if platform not in self.backends:
            self.backends[platform] = self._create_runtime(platform,*args, **kwargs)
            self.logger.info(f"Initialized {platform} runtime")
        
        return self.backends[platform]
    
    def _create_runtime(self, platform: str,*args, **kwargs):
        """
        创建运行时实例
        
        Args:
            platform: 平台名称
            **kwargs: 初始化参数
            
        Returns:
            运行时实例
        """
        if platform == "remote":
            monitoring_interval = kwargs.get('monitoring_interval', 2.0)
            return RayRuntime.get_instance(monitoring_interval=monitoring_interval)
        
        elif platform == "local":
            return LocalRuntime.get_instance()
        
        else:
            raise ValueError(f"Unknown platform: {platform}")
    
    def list_platforms(self):
        """
        列出所有已初始化的平台
        
        Returns:
            已初始化的平台列表
        """
        return list(self.backends.keys())
    
    def is_platform_initialized(self, platform: str) -> bool:
        """
        检查指定平台是否已初始化
        
        Args:
            platform: 平台名称
            
        Returns:
            是否已初始化
        """
        return platform in self.backends

    def submit(self, dag):
        """
        提交图到合适的运行时执行
        
        Args:
            dag: raydag或dag 实例
            
        Returns:
            str: 任务句柄
        """
        platform = dag.platform
        platform_runtime = self.get(platform)
        
        if not platform_runtime:
            raise RuntimeError(f"No runtime available for platform: {platform}")
        self.logger.info(f"DAG '{dag.name}' submitted to runtime:{platform_runtime.name}.")
        
        return platform_runtime.submit_task(dag)