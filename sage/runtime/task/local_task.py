import os
import queue
from typing import TYPE_CHECKING
from sage.runtime.task.base_task import BaseTask
if TYPE_CHECKING:
    from sage.jobmanager.factory.operator_factory import OperatorFactory
    from sage.runtime.runtime_context import RuntimeContext


class LocalTask(BaseTask):
    """
    本地任务节点，使用Python标准queue作为输入缓冲区
    内部运行独立的工作线程，处理数据流
    """
    
    def __init__(self,
                 runtime_context: 'RuntimeContext', 
                 operator_factory: 'OperatorFactory',
                 queue_maxsize: int = 50000) -> None:
        
        self.queue_maxsize = queue_maxsize
        # 调用父类初始化
        super().__init__(runtime_context, operator_factory)

        self.logger.info(f"Initialized LocalTask: {self.ctx.name}")
        self.logger.debug(f"Queue max size: {queue_maxsize}")
    
    def _initialize_queue(self):
        """初始化Python标准队列"""
        self.input_buffer = queue.Queue(maxsize=self.queue_maxsize)
        self.logger.debug(f"Initialized standard Python queue for {self.ctx.name}")
    
    def get_input_buffer(self):
        """获取输入缓冲区"""
        return self.input_buffer
    
    def get_object(self):
        """获取任务对象本身，用于本地连接"""
        return self