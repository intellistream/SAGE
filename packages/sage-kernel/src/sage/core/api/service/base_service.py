from abc import ABC, abstractmethod
from typing import TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from sage.kernel import ServiceContext


class BaseService(ABC):
    """
    BaseService is the abstract base class for all services in SAGE.
    It defines the core interface and provides access to runtime context and logger.
    """
    
    def __init__(self, *args, **kwargs):
        """
        初始化基础服务
        
        Args:
            *args: 位置参数
            **kwargs: 关键字参数
        
        Note:
            ctx 会在实例创建时由 ServiceFactory 自动注入，
            服务类不需要在构造函数中声明 ctx 参数
        """
        # ctx 由 ServiceFactory 在 __init__ 调用前通过 __new__ 方法注入
        if not hasattr(self, 'ctx'):
            self.ctx: 'ServiceContext' = None
        self._logger = None
    
    @property
    def logger(self):
        """获取logger，优先使用ctx.logger，否则使用默认logger"""
        if not hasattr(self, "_logger") or self._logger is None:
            if self.ctx is None:
                self._logger = logging.getLogger(self.__class__.__name__)
            else:
                self._logger = self.ctx.logger
        return self._logger
    
    @property
    def name(self):
        """获取服务名称，如果有ctx则使用ctx.name，否则使用类名"""
        if self.ctx is not None:
            return self.ctx.name
        return self.__class__.__name__
    
    @property
    def call_service(self):
        """
        同步服务调用语法糖
        
        用法:
            result = self.call_service["cache_service"].get("key1")
            data = self.call_service["db_service"].query("SELECT * FROM users")
        """
        if self.ctx is None:
            raise RuntimeError("Service context not initialized. Cannot access services.")
        
        return self.ctx.call_service()
    
    @property 
    def call_service_async(self):
        """
        异步服务调用语法糖
        
        用法:
            future = self.call_service_async["cache_service"].get("key1")
            result = future.result()  # 阻塞等待结果
            
            # 或者非阻塞检查
            if future.done():
                result = future.result()
        """
        if self.ctx is None:
            raise RuntimeError("Service context not initialized. Cannot access services.")
        
        return self.ctx.call_service_async()
    
    def setup(self):
        """
        服务初始化设置方法，在service_instance创建后调用
        子类可以重写此方法来进行初始化设置
        """
        pass
    
    def cleanup(self):
        """
        服务清理方法，在服务停止时调用
        子类可以重写此方法来进行资源清理
        """
        pass
    
    def start(self):
        """
        服务启动方法，在服务启动时调用
        子类可以重写此方法来进行启动逻辑
        """
        pass
    
    def stop(self):
        """
        服务停止方法，在服务停止时调用
        子类可以重写此方法来进行停止逻辑
        """
        pass
