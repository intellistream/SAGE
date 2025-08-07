from abc import ABC, abstractmethod
from typing import TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from sage.kernel.runtime.service_context import ServiceContext


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
