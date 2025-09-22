import queue
from typing import Any, TYPE_CHECKING
from sage.common.utils.logging.custom_logger import CustomLogger
from .base_service_task import BaseServiceTask

if TYPE_CHECKING:
    from sage.core.factory.service_factory import ServiceFactory
    from sage.kernel.runtime.context.service_context import ServiceContext


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
    
    def _create_request_queue(self) -> queue.Queue:
        """创建Python标准队列作为请求队列"""
        return queue.Queue()
    
    def _create_response_queue(self, queue_name: str) -> queue.Queue:
        """创建Python标准队列作为响应队列"""
        return queue.Queue()
    
    def _queue_get(self, queue: queue.Queue, timeout: float = 1.0) -> Any:
        """从Python标准队列获取数据"""
        return queue.get(timeout=timeout)
    
    def _queue_put(self, queue: queue.Queue, data: Any, timeout: float = 5.0) -> None:
        """向Python标准队列放入数据"""
        queue.put(data, timeout=timeout)
    
    def _queue_close(self, queue: queue.Queue) -> None:
        """关闭Python标准队列（实际上标准队列不需要关闭）"""
        # Python标准队列不需要显式关闭
        pass
