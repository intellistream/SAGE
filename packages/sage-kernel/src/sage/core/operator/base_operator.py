
from abc import ABC, abstractmethod
from typing import Any, List, Dict, Optional, TYPE_CHECKING, Type, Tuple
from sage.core.communication.stop_signal import StopSignal

if TYPE_CHECKING:
    from sage.core.communication.packet import Packet
    from sage.core.api.function.base_function import BaseFunction
    from sage.kernel import TaskContext
    from sage.core.factory.function_factory import FunctionFactory
    from sage.common.utils.logging.custom_logger import CustomLogger

class BaseOperator(ABC):
    def __init__(self, 
                 function_factory: 'FunctionFactory', ctx: 'TaskContext', *args,
                 **kwargs):
        
        self.ctx: 'TaskContext' = ctx
        self.function:'BaseFunction'
        try:
            self.function = function_factory.create_function(self.name, ctx)
            self.logger.debug(f"Created function instance with {function_factory}")

        except Exception as e:
            self.logger.error(f"Failed to create function instance: {e}", exc_info=True)
            raise

    def send_packet(self, packet: 'Packet') -> bool:
        """
        通过TaskContext发送数据包，间接调用router功能
        """
        return self.ctx.send_packet(packet)

    def send_stop_signal(self, stop_signal: 'StopSignal') -> None:
        """
        通过TaskContext发送停止信号，间接调用router功能
        """
        self.ctx.send_stop_signal(stop_signal)
    
    def get_routing_info(self) -> Dict[str, Any]:
        """
        获取路由信息，用于调试和监控
        """
        return self.ctx.get_routing_info()
    
    @property
    def router(self):
        return self.ctx.router

    # TODO: 去掉stateful function的概念，用某些策略对于function内部的可序列化字段做静态保存和checkpoint
    # Issue URL: https://github.com/intellistream/SAGE/issues/388
    # def save_state(self):
    #     from sage.core.api.function.base_function import StatefulFunction
    #     if isinstance(self.function, StatefulFunction):
    #         self.function.save_state()

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