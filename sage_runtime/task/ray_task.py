import ray
import time
import threading
from typing import Any, Union, Tuple, TYPE_CHECKING, Dict, Optional
from ray.util.queue import Queue as RayQueue
from sage_runtime.task.base_task import BaseTask
from sage_utils.custom_logger import CustomLogger
from sage_runtime.router.packet import Packet
from sage_runtime.router.ray_router import RayRouter
if TYPE_CHECKING:
    from sage_jobmanager.factory.operator_factory import OperatorFactory
    from sage_jobmanager.factory.runtime_context import RuntimeContext



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
        self.input_buffer = RayQueue(maxsize=1000)
        # === 路由器 ===
        self.router = RayRouter(runtime_context)
        self.operator.router = self.router

        self.logger.info(f"Initialized RayTask: {self.ctx.name}")

