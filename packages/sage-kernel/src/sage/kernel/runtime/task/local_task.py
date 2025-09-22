import os
from typing import TYPE_CHECKING
from sage.kernel.runtime.task.base_task import BaseTask
if TYPE_CHECKING:
    from sage.core.factory.operator_factory import OperatorFactory
    from sage.kernel.runtime.context.task_context import TaskContext


class LocalTask(BaseTask):
    """
    本地任务节点，使用SageQueue高性能共享队列作为输入缓冲区
    内部运行独立的工作线程，处理数据流
    """
    
    def __init__(self,
                 runtime_context: 'TaskContext', 
                 operator_factory: 'OperatorFactory',
                 max_buffer_size: int = 30000,
                 queue_maxsize: int = 50000) -> None:
        
        # 调用父类初始化
        super().__init__(runtime_context, operator_factory)

        self.logger.info(f"Initialized LocalTask: {self.ctx.name}")
        self.logger.debug(f"Buffer max size: {max_buffer_size} bytes, Queue max size: {queue_maxsize}")