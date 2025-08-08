from abc import ABC, abstractmethod
from typing import Optional, TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from sage.kernel.runtime.service.service_caller import ServiceManager
    from sage.utils.logging.custom_logger import CustomLogger


class BaseRuntimeContext(ABC):
    """
    Base runtime context class providing common functionality
    for TaskContext and ServiceContext
    """
    
    def __init__(self):
        # 服务调用相关
        self._service_manager: Optional['ServiceManager'] = None
        self._service_dict = None
        self._async_service_dict = None
    
    @property
    @abstractmethod
    def logger(self) -> 'CustomLogger':
        """Logger property - must be implemented by subclasses"""
        pass
    
    @property
    def service_manager(self) -> 'ServiceManager':
        """Lazy-loaded service manager"""
        if self._service_manager is None:
            from sage.kernel.runtime.service.service_caller import ServiceManager
            self._service_manager = ServiceManager(self, logger=self.logger)
        return self._service_manager
    
    def call_service(self):
        """
        获取同步服务调用代理字典
        Usage: ctx.call_service()["service_name"].method(*args)
        """
        if not hasattr(self, '_service_dict') or self._service_dict is None:
            from sage.kernel.runtime.service.service_caller import ServiceCallProxy
            
            class ServiceDict:
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
            
            self._service_dict = ServiceDict(self.service_manager, logger=self.logger)
        
        return self._service_dict
    
    def call_service_async(self):
        """
        获取异步服务调用代理字典
        Usage: future = ctx.call_service_async()["service_name"].method(*args)
                result = future.result(timeout=10)  # 阻塞等待结果
        """
        if not hasattr(self, '_async_service_dict') or self._async_service_dict is None:
            class AsyncServiceDict:
                def __init__(self, service_manager: 'ServiceManager', logger=None):
                    self._service_manager = service_manager
                    self._async_service_proxies = {}  # 缓存AsyncServiceCallProxy对象
                    self.logger = logger if logger is not None else logging.getLogger(__name__)
                    
                def __getitem__(self, service_name: str):
                    if service_name not in self._async_service_proxies:
                        self._async_service_proxies[service_name] = AsyncServiceCallProxy(
                            self._service_manager, service_name, logger=self.logger
                        )
                    return self._async_service_proxies[service_name]
            
            # 需要定义 AsyncServiceCallProxy 类
            class AsyncServiceCallProxy:
                """异步服务调用代理，返回 Future 对象"""
                
                def __init__(self, service_manager: 'ServiceManager', service_name: str, logger=None):
                    self._service_manager = service_manager
                    self._service_name = service_name
                    self.logger = logger if logger is not None else logging.getLogger(f"{__name__}.async.{service_name}")
                    
                    self.logger.debug(f"[ASYNC_PROXY] Created AsyncServiceCallProxy for service: {service_name}")
                
                def __getattr__(self, method_name: str):
                    """获取服务方法的异步调用代理，返回 Future 对象"""
                    self.logger.debug(f"[ASYNC_PROXY] Creating async method proxy for {self._service_name}.{method_name}")
                    
                    def async_method_call(*args, timeout: float = 30.0, **kwargs):
                        """异步方法调用，返回 Future 对象"""
                        self.logger.info(f"[ASYNC_PROXY] Starting async call: {self._service_name}.{method_name} with timeout={timeout}s")
                        
                        # 使用 ServiceManager 的 call_async 方法返回 Future
                        future = self._service_manager.call_async(
                            self._service_name,
                            method_name,
                            *args,
                            timeout=timeout,
                            **kwargs
                        )
                        
                        self.logger.debug(f"[ASYNC_PROXY] Future created for {self._service_name}.{method_name}")
                        return future
                    
                    # 设置方法名称用于调试
                    async_method_call.__name__ = f"async_{self._service_name}.{method_name}"
                    return async_method_call
            
            self._async_service_dict = AsyncServiceDict(self.service_manager, logger=self.logger)
        
        return self._async_service_dict
    
    def cleanup_service_manager(self):
        """清理服务管理器资源"""
        if self._service_manager is not None:
            try:
                self._service_manager.shutdown()
            except Exception as e:
                self.logger.warning(f"Error shutting down service manager: {e}")
            finally:
                self._service_manager = None
