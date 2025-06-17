import logging
from typing import Dict, Any
from sage.core.runtime.base_runtime import BaseRuntime
from sage.core.runtime.ray.ray_runtime import RayRuntime
from sage.core.runtime.local.local_runtime import LocalRuntime
from sage.core.dag.local.dag import DAG

class RuntimeManager:
    """
    运行时管理器，负责管理不同平台的运行时实例
    """
    
    def __init__(self):
        self.backends: Dict[str, Any] = {}
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def get(self, platform: str, **kwargs) -> BaseRuntime:
        """
        获取指定平台的运行时实例，支持延迟初始化
        
        Args:
            platform: 平台名称 ("ray", "local")
            **kwargs: 运行时初始化参数
            
        Returns:
            运行时实例
        """
        if platform not in self.backends:
            self.backends[platform] = self._create_runtime(platform, **kwargs)
            self.logger.info(f"Initialized {platform} runtime")
        
        return self.backends[platform]
    
    def _create_runtime(self, platform: str, **kwargs):
        """
        创建运行时实例
        
        Args:
            platform: 平台名称
            **kwargs: 初始化参数
            
        Returns:
            运行时实例
        """
        if platform == "ray":
            monitoring_interval = kwargs.get('monitoring_interval', 2.0)
            return RayRuntime(monitoring_interval=monitoring_interval)
        
        elif platform == "local":
            max_slots = kwargs.get('max_slots', 4)
            scheduling_strategy = kwargs.get('scheduling_strategy', None)
            return LocalRuntime(max_slots=max_slots, scheduling_strategy=scheduling_strategy)
        
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
    
    def shutdown_platform(self, platform: str):
        """
        关闭指定平台的运行时
        
        Args:
            platform: 平台名称
        """
        if platform in self.backends:
            runtime = self.backends[platform]
            if hasattr(runtime, 'shutdown'):
                runtime.shutdown()
            del self.backends[platform]
            self.logger.info(f"Shutdown {platform} runtime")
    
    def shutdown_all(self):
        """
        关闭所有运行时
        """
        for platform in list(self.backends.keys()):
            self.shutdown_platform(platform)
        self.logger.info("All runtimes shutdown")

    def submit(self, dag:DAG):
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