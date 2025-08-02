import ray
import time
from typing import Any, TYPE_CHECKING
from sage.utils.custom_logger import CustomLogger
from .base_service_task import BaseServiceTask

if TYPE_CHECKING:
    from sage.runtime.factory.service_factory import ServiceFactory
    from archive.runtime_context import RuntimeContext


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
        try:
            super().__init__(service_factory, ctx)
            self.logger.debug(f"Ray service task '{self.service_name}' initialized")
        except Exception as e:
            # 如果父类初始化失败，确保至少有基本属性
            if not hasattr(self, 'service_name'):
                self.service_name = "Unknown_Ray_Service"
            if not hasattr(self, 'logger'):
                self.logger = CustomLogger(name=f"RayServiceTask_{self.service_name}")
            self.logger.error(f"Failed to initialize Ray service task: {e}")
            raise
    
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
    
    def get_statistics(self) -> dict:
        """获取服务统计信息（覆盖基类方法添加Ray特定信息）"""
        stats = super().get_statistics()
        stats.update({
            "actor_id": f"ray_actor_{self.service_name}",
            "ray_node_id": ray.get_runtime_context().node_id.hex() if ray.is_initialized() else "unknown"
        })
        return stats
