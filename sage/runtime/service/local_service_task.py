from typing import Any, TYPE_CHECKING
from sage_utils.custom_logger import CustomLogger
from .base_service_task import BaseServiceTask

if TYPE_CHECKING:
    from sage.jobmanager.factory.service_factory import ServiceFactory
    from sage_runtime.runtime_context import RuntimeContext


class LocalServiceTask(BaseServiceTask):
    """本地服务任务，继承BaseServiceTask并提供本地执行支持"""
    
    def __init__(self, service_factory: 'ServiceFactory', ctx: 'RuntimeContext' = None):
        """
        初始化本地服务任务
        
        Args:
            service_factory: 服务工厂实例
            ctx: 运行时上下文
        """
        super().__init__(service_factory, ctx)
        self.logger.debug(f"Local service task '{self.service_name}' initialized")
    
    def _start_service_instance(self):
        """启动本地服务实例"""
        # 如果服务实例有启动方法，调用它
        if hasattr(self.service_instance, 'start_running'):
            self.service_instance.start_running()
        elif hasattr(self.service_instance, 'start'):
            self.service_instance.start()
    
    def _stop_service_instance(self):
        """停止本地服务实例"""
        # 如果服务实例有停止方法，调用它
        if hasattr(self.service_instance, 'stop'):
            self.service_instance.stop()
