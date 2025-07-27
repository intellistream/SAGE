import ray
import time
import threading
from typing import Any, Union, Tuple, TYPE_CHECKING, Dict, Optional
from ray.util.queue import Queue as RayQueue
from sage.runtime.task.base_task import BaseTask
from sage.runtime.router.packet import Packet
if TYPE_CHECKING:
    from sage.jobmanager.factory.operator_factory import OperatorFactory
    from sage.runtime.runtime_context import RuntimeContext



@ray.remote
class RayTask(BaseTask):
    """
    基于Ray Actor的任务节点，使用Ray Queue作为输入输出缓冲区
    内部运行独立的工作线程，避免阻塞Ray Actor的事件循环
    """
    
    def __init__(self,
                 runtime_context: 'RuntimeContext', 
                 operator_factory: 'OperatorFactory',
                 queue_maxsize: int = 50000) -> None:
        
        self.queue_maxsize = queue_maxsize
        # 调用父类初始化
        super().__init__(runtime_context, operator_factory)

        self.logger.info(f"Initialized RayTask: {self.ctx.name}")
    
    def _initialize_queue(self):
        """初始化Ray队列"""
        self.input_buffer = RayQueue(maxsize=self.queue_maxsize)
        self.logger.debug(f"Initialized Ray queue for {self.ctx.name}")
    
    def get_input_buffer(self):
        """获取输入缓冲区"""
        return self.input_buffer
    
    def get_object(self):
        """获取任务对象本身，用于Ray连接"""
        return self