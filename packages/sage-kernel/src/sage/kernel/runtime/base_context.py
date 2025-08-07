from abc import ABC, abstractmethod
from typing import Optional, TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from sage.kernel.runtime.service.service_caller import ServiceManager
    from sage.kernel.utils.logging.custom_logger import CustomLogger


class BaseRuntimeContext(ABC):
    """
    Base runtime context class providing common functionality
    for TaskContext and ServiceContext
    """
    
    def __init__(self):
        # 服务调用相关
        self._service_manager: Optional['ServiceManager'] = None
        self._call_service_proxy = None
        self._call_service_async_proxy = None
    
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
    
    @property
    def call_service(self):
        """
        Synchronous service call syntax sugar
        Usage: self.call_service["service_name"].method(*args)
        """
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
            
            self._call_service_proxy = ServiceProxy(self.service_manager, logger=self.logger)
        
        return self._call_service_proxy
    
    @property 
    def call_service_async(self):
        """
        Asynchronous service call syntax sugar
        Usage: future = self.call_service_async["service_name"].method(*args)
        """
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
            
            self._call_service_async_proxy = AsyncServiceProxy(self.service_manager, logger=self.logger)
        
        return self._call_service_async_proxy
    
    def cleanup_service_manager(self):
        """清理服务管理器资源"""
        if self._service_manager is not None:
            try:
                self._service_manager.shutdown()
            except Exception as e:
                self.logger.warning(f"Error shutting down service manager: {e}")
            finally:
                self._service_manager = None
