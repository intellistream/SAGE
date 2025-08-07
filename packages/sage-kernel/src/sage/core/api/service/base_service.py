from abc import ABC, abstractmethod
from typing import TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from sage.kernel.runtime.service_context import ServiceContext
    from sage.kernel.runtime.service.service_caller import ServiceManager


class BaseService(ABC):
    """
    BaseService is the abstract base class for all services in SAGE.
    It defines the core interface and provides access to runtime context and logger.
    """
    
    def __init__(self, *args, **kwargs):
        self.ctx: 'ServiceContext' = None  # 运行时注入
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
        
        # 懒加载缓存机制
        if not hasattr(self, '_call_service_proxy') or self._call_service_proxy is None:
            from sage.kernel.runtime.service.service_caller import ServiceCallProxy
            
            class ServiceProxy:
                def __init__(self, service_manager: 'ServiceManager', logger=None):
                    self._service_manager = service_manager
                    self._service_proxies = {}  # 缓存ServiceCallProxy对象
                    self.logger = logger if logger is not None else logging.getLogger(__name__)
                    
                def __getitem__(self, service_name: str):
                    if service_name not in self._service_proxies:
                        self._service_proxies[service_name] = ServiceCallProxy(
                            self._service_manager, service_name, logger=self.logger
                        )
                    return self._service_proxies[service_name]
            
            self._call_service_proxy = ServiceProxy(self.ctx.service_manager, logger=self.logger)
        
        return self._call_service_proxy
    
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
        
        # 懒加载缓存机制
        if not hasattr(self, '_call_service_async_proxy') or self._call_service_async_proxy is None:
            class AsyncServiceProxy:
                def __init__(self, service_manager: 'ServiceManager', logger=None):
                    self._service_manager = service_manager
                    self._async_service_proxies = {}  # 缓存ServiceCallProxy对象
                    self.logger = logger if logger is not None else logging.getLogger(__name__)
                    
                def __getitem__(self, service_name: str):
                    if service_name not in self._async_service_proxies:
                        from sage.kernel.runtime.service.service_caller import ServiceCallProxy
                        self._async_service_proxies[service_name] = ServiceCallProxy(
                            self._service_manager, service_name, logger=self.logger
                        )
                    return self._async_service_proxies[service_name]
            
            self._call_service_async_proxy = AsyncServiceProxy(self.ctx.service_manager, logger=self.logger)
        
        return self._call_service_async_proxy
    
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
