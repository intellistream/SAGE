
from abc import ABC, abstractmethod
from typing import Any, List, Dict, Optional, TYPE_CHECKING, Type, Tuple
from sage.core.api.function.source_function import StopSignal

if TYPE_CHECKING:
    from sage.kernel.runtime.communication.router.packet import Packet
    from sage.core.api.function.base_function import BaseFunction
    from sage.kernel.runtime.task_context import TaskContext
    from sage.kernel.runtime.factory.function_factory import FunctionFactory
    from sage.kernel.runtime.communication.router.router import BaseRouter
    from sage.kernel.runtime.task.base_task import BaseTask
    from sage.kernel.utils.logging.custom_logger import CustomLogger

class BaseOperator(ABC):
    def __init__(self, 
                 function_factory: 'FunctionFactory', ctx: 'TaskContext', *args,
                 **kwargs):
        
        self.ctx: 'TaskContext' = ctx
        self.function:'BaseFunction'
        self.router:'BaseRouter'     # 由task传下来的
        self.task: Optional['BaseTask'] = None
        try:
            self.function = function_factory.create_function(self.name, ctx)
            self.logger.debug(f"Created function instance with {function_factory}")

        except Exception as e:
            self.logger.error(f"Failed to create function instance: {e}", exc_info=True)
            raise

    def inject_router(self, router: 'BaseRouter'):
        """
        注入路由器实例
        """
        self.router = router
        self.logger.debug(f"Injected router into operator {self.name}")


    # TODO: 去掉stateful function的概念，用某些策略对于function内部的可序列化字段做静态保存和checkpoint
    # Issue URL: https://github.com/intellistream/SAGE/issues/388
    def save_state(self):
        from sage.core.api.function.base_function import StatefulFunction
        if isinstance(self.function, StatefulFunction):
            self.function.save_state()

    def receive_packet(self, packet: 'Packet'):
        """
        接收数据包并处理
        """
        if packet is None:
            self.logger.warning(f"Received None packet in {self.name}")
            return
        self.logger.debug(f"Operator {self.name} received packet: {packet}")
        # 处理数据包
        self.process_packet(packet)

    @abstractmethod
    def process_packet(self, packet: 'Packet' = None):
        return

    @property
    def name(self) -> str:
        """获取任务名称"""
        return self.ctx.name

    @property
    def logger(self) -> 'CustomLogger':
        """获取当前任务的日志记录器"""
        return self.ctx.logger