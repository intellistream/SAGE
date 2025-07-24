import ray
import time
import threading
from typing import Any, Union, Tuple, TYPE_CHECKING, Dict, Optional
from ray.util.queue import Queue as RayQueue
from sage_runtime.task.base_task import BaseTask
from sage_runtime.router.packet import Packet
from sage_runtime.router.ray_router import RayRouter
from sage_utils.mmap_queue.sage_queue import SageQueue
if TYPE_CHECKING:
    from sage_jobmanager.factory.operator_factory import OperatorFactory
    from sage_runtime.runtime_context import RuntimeContext



@ray.remote
class RayTask(BaseTask):
    """
    基于Ray Actor的任务节点，使用Ray Queue作为输入输出缓冲区
    内部运行独立的工作线程，避免阻塞Ray Actor的事件循环
    """
    
    def __init__(self,
                 runtime_context: 'RuntimeContext', 
                 operator_factory: 'OperatorFactory') -> None:
        
        # 调用父类初始化
        super().__init__(runtime_context, operator_factory)

        # === Ray Queue 缓冲区 ===
        # 创建Ray Queue（这是一个Ray对象，自动支持跨进程）
        # 这个maxsize指的是物理字节容量
        self.local_input_buffer = SageQueue(self.ctx.name)
        # === 路由器 ===
        self.router = RayRouter(runtime_context)
        self.operator.router = self.router

        self.logger.info(f"Initialized RayTask: {self.ctx.name}")

    def cleanup(self):
        super().cleanup()
        """清理任务资源 - 重写以支持 Ray 特定清理"""
        self.logger.info(f"Cleaning up RayTask {self.name}")
        
        try:
            # 停止任务
            if self.is_running:
                self.stop()
            
            # # 清理算子资源
            # if hasattr(self.operator, 'cleanup'):
            #     self.operator.cleanup()
            # 这些内容应该会自己清理掉
            # # 清理 Ray Router
            # if hasattr(self.router, 'cleanup'):
            #     self.router.cleanup()
            
            # 清理 Ray Queue
            if hasattr(self.local_input_buffer, 'shutdown'):
                try:
                    self.local_input_buffer.shutdown()
                except Exception as e:
                    self.logger.warning(f"Error shutting down input buffer: {e}")
            
            self.logger.debug(f"RayTask {self.name} cleanup completed")
            
        except Exception as e:
            self.logger.error(f"Error during cleanup of RayTask {self.name}: {e}")