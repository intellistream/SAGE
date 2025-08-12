import ray
import time
from typing import Any, TYPE_CHECKING
from sage.common.utils.logging.custom_logger import CustomLogger
from .base_service_task import BaseServiceTask

# 安全导入Ray队列
try:
    from ray.util.queue import Queue as RayQueue
    RAY_QUEUE_AVAILABLE = True
except ImportError:
    RayQueue = None
    RAY_QUEUE_AVAILABLE = False

if TYPE_CHECKING:
    from sage.core.factory.service_factory import ServiceFactory
    from sage.kernel.runtime.context.service_context import ServiceContext


@ray.remote
class RayServiceTask(BaseServiceTask):
    """Ray服务任务，继承BaseServiceTask并提供Ray分布式执行支持"""
    
    def __init__(self, service_factory: 'ServiceFactory', ctx: 'RuntimeContext' = None):
        """
        初始化Ray服务任务
        
        Args:
            service_factory: 服务工厂实例
            ctx: 运行时上下文
        """
        super().__init__(service_factory, ctx)
        self.logger.debug(f"Ray service task '{self.service_name}' initialized")
    
    def _start_service_instance(self):
        """启动Ray服务实例"""
        # 如果服务实例有启动方法，调用它
        if hasattr(self.service_instance, 'start_running'):
            self.service_instance.start_running()
        elif hasattr(self.service_instance, 'start'):
            self.service_instance.start()
    
    def _stop_service_instance(self):
        """停止Ray服务实例"""
        # 如果服务实例有停止方法，调用它
        if hasattr(self.service_instance, 'stop'):
            self.service_instance.stop()
    
    def _create_request_queue(self) -> Any:
        """创建Ray队列作为请求队列"""
        if not RAY_QUEUE_AVAILABLE:
            raise RuntimeError("Ray queue is not available. Please ensure Ray is properly installed.")
        return RayQueue(maxsize=10000)
    
    def _create_response_queue(self, queue_name: str) -> Any:
        """创建Ray队列作为响应队列"""
        if not RAY_QUEUE_AVAILABLE:
            raise RuntimeError("Ray queue is not available. Please ensure Ray is properly installed.")
        return RayQueue(maxsize=10000)
    
    def _queue_get(self, queue: Any, timeout: float = 1.0) -> Any:
        """从Ray队列获取数据"""
        return queue.get(timeout=timeout)
    
    def _queue_put(self, queue: Any, data: Any, timeout: float = 5.0) -> None:
        """向Ray队列放入数据"""
        queue.put(data, timeout=timeout)
    
    def _queue_close(self, queue: Any) -> None:
        """关闭Ray队列"""
        if hasattr(queue, 'shutdown'):
            queue.shutdown()
        elif hasattr(queue, 'close'):
            queue.close()
    
    def get_statistics(self) -> dict:
        """获取服务统计信息（覆盖基类方法添加Ray特定信息）"""
        stats = super().get_statistics()
        stats.update({
            "actor_id": f"ray_actor_{self.service_name}",
            "ray_node_id": ray.get_runtime_context().node_id.hex() if ray.is_initialized() else "unknown"
        })
        return stats
