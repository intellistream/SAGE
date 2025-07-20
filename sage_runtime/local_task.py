import threading
import time
from typing import Any, TYPE_CHECKING, Dict, Optional
from sage_runtime.base_task import BaseTask
from sage_runtime.io.local_message_queue import LocalMessageQueue
from sage_runtime.local_router import LocalRouter
from sage_utils.custom_logger import CustomLogger
from sage_runtime.io.packet import Packet

if TYPE_CHECKING:
    from sage_runtime.operator.factory import OperatorFactory
    from sage_runtime.runtime_context import RuntimeContext
    from sage_runtime.io.connection import Connection


class LocalTask(BaseTask):
    """
    本地任务节点，使用LocalMessageQueue作为输入缓冲区
    内部运行独立的工作线程，处理数据流
    """
    
    def __init__(self,
                 runtime_context: 'RuntimeContext', 
                 operator_factory: 'OperatorFactory',
                 max_buffer_size: int = 30000,
                 queue_maxsize: int = 50000) -> None:
        
        # 调用父类初始化
        super().__init__(runtime_context, operator_factory)

        # === Local Message Queue 缓冲区 ===
        # 创建本地消息队列作为输入缓冲区
        self.input_buffer = LocalMessageQueue(
            name=f"{self.ctx.name}_input",
            max_buffer_size=30000,
            session_folder=runtime_context.session_folder,
            env_name=runtime_context.env_name
        )
    
        
        # === 本地路由器 ===
        self.router = LocalRouter(runtime_context)
        self.operator.router = self.router

        self.logger.info(f"Initialized LocalTask: {self.ctx.name}")
        self.logger.debug(f"Buffer max size: {max_buffer_size} bytes, Queue max size: {queue_maxsize}")