
from abc import ABC, abstractmethod
from typing import Any, List, Dict, Optional, Set, TYPE_CHECKING, Type, Tuple
from core.function.source_function import StopSignal
from runtime.task.base_task import BaseTask
from utils.custom_logger import CustomLogger
from runtime.router.packet import Packet

if TYPE_CHECKING:
    from core.function.base_function import BaseFunction
    from runtime.router.connection import Connection
    from runtime.runtime_context import RuntimeContext
    from jobmanager.factory.function_factory import FunctionFactory
    from runtime.router.router import BaseRouter

class BaseOperator(ABC):
    def __init__(self, 
                 function_factory: 'FunctionFactory', ctx: 'RuntimeContext', *args,
                 **kwargs):
        
        self.received_stop_signals: Set[str] = set()
        self.ctx: 'RuntimeContext' = ctx
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
    def save_state(self):
        from core.function.base_function import StatefulFunction
        if isinstance(self.function, StatefulFunction):
            self.function.save_state()

    def receive_packet(self, packet: 'Packet'):
        """l
        接收数据包并处理
        """
        if packet is None:
            self.logger.warning(f"Received None packet in {self.name}")
            return
        if isinstance(packet, StopSignal):
            self.handle_stop_signal(packet) 
            return
        self.logger.debug(f"Operator {self.name} received packet: {packet}")
        # 处理数据包
        self.process_packet(packet)

    def handle_stop_signal(self, stop_signal: StopSignal):
        """
        处理停止信号
        """
        if stop_signal.name in self.received_stop_signals:
            self.logger.debug(f"Already received stop signal from {stop_signal.name}")
            return
        
        self.received_stop_signals.add(stop_signal.name)
        self.logger.info(f"Handling stop signal from {stop_signal.name}")
        # 发送停止信号到路由器
        self.router.send_stop_signal(stop_signal)

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