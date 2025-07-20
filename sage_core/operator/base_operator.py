
from abc import ABC, abstractmethod
from typing import Any, List, Dict, Optional, Set, TYPE_CHECKING, Type, Tuple
from sage_utils.custom_logger import CustomLogger
from sage_runtime.router.packet import Packet

if TYPE_CHECKING:
    from sage_core.function.base_function import BaseFunction
    from sage_runtime.router.connection import Connection
    from sage_jobmanager.factory.runtime_context import RuntimeContext
    from sage_jobmanager.factory.function_factory import FunctionFactory

class BaseOperator(ABC):
    def __init__(self, 
                 function_factory: 'FunctionFactory', ctx: 'RuntimeContext', *args,
                 **kwargs):
        
        self.ctx: 'RuntimeContext' = ctx
        self.function:'BaseFunction'
        self.router:Any     # 由task传下来的
        try:
            self.function = function_factory.create_function(self.name, ctx)
            self.logger.debug(f"Created function instance with {function_factory}")

        except Exception as e:
            self.logger.error(f"Failed to create function instance: {e}", exc_info=True)

    # TODO: 去掉stateful function的概念，用某些策略对于function内部的可序列化字段做静态保存和checkpoint
    def save_state(self):
        from sage_core.function.base_function import StatefulFunction
        if isinstance(self.function, StatefulFunction):
            self.function.save_state()

    @abstractmethod
    def process_packet(self, packet: 'Packet' = None):
        return

    @property
    def name(self) -> str:
        """获取任务名称"""
        return self.ctx.name

    @property
    def logger(self) -> CustomLogger:
        """获取当前任务的日志记录器"""
        return self.ctx.logger