"""
Base Service - 服务基类

提供服务的基础接口，被BaseServiceTask包装执行
这是原来sage.core.api.service.base_service的替代
"""

from typing import TYPE_CHECKING, Optional
from sage.common.utils.logging.custom_logger import CustomLogger

if TYPE_CHECKING:
    from sage.core.factory.service_factory import ServiceFactory
    from sage.kernel.runtime.context.service_context import ServiceContext


class BaseService:
    """
    服务基类
    
    提供基础的服务接口，包含service_name和logger等基本属性
    所有具体的服务实现都应该继承此基类
    """
    
    def __init__(self, service_factory: 'ServiceFactory', ctx: 'ServiceContext' = None):
        """
        初始化基础服务
        
        Args:
            service_factory: 服务工厂实例
            ctx: 服务上下文
        """
        self.service_factory = service_factory
        self.service_name = service_factory.service_name
        self.ctx = ctx
        
        # 创建logger
        self._logger = None
        
    @property
    def logger(self) -> CustomLogger:
        """获取logger，优先使用ctx.logger，否则使用CustomLogger"""
        if self._logger is None:
            if self.ctx and hasattr(self.ctx, 'logger'):
                self._logger = self.ctx.logger
            else:
                self._logger = CustomLogger(name=f"Service-{self.service_name}")
        return self._logger
    
    def setup(self):
        """服务设置方法，子类可以覆盖"""
        pass
    
    def start(self):
        """启动服务，子类可以覆盖"""
        pass
    
    def start_running(self):
        """启动服务运行，start的别名"""
        self.start()
    
    def stop(self):
        """停止服务，子类可以覆盖"""
        pass
    
    def cleanup(self):
        """清理资源，子类可以覆盖"""
        pass
    
    def close(self):
        """关闭服务，cleanup的别名"""
        self.cleanup()
        
    def get_statistics(self):
        """获取服务统计信息，子类可以覆盖"""
        return {
            "service_name": self.service_name,
            "service_class": self.__class__.__name__
        }
