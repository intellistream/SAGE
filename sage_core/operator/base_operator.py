
from abc import ABC, abstractmethod
from typing import Any, List, Dict, Optional, Set, TYPE_CHECKING, Type, Tuple
from sage_utils.custom_logger import CustomLogger
from sage_runtime.io.unified_emit_context import UnifiedEmitContext
from sage_runtime.io.packet import Packet

if TYPE_CHECKING:
    from sage_core.function.base_function import BaseFunction
    from sage_runtime.io.connection import Connection
    from sage_runtime.runtime_context import RuntimeContext
    from sage_runtime.function.factory import FunctionFactory




# TODO: 将Memory的API使用在这里。



# Operator 决定事件的逻辑路由（如广播、分区、keyBy等），
# EmitContext 仅负责将数据发送到指定的下游通道或节点。
# 路由策略是 Operator 的语义特征，EmitContext 专注于消息投递的物理实现。

class BaseOperator(ABC):
    def __init__(self, 
                 function_factory: 'FunctionFactory',*args,
                 **kwargs):
        
        self.name:str
        self.function:'BaseFunction'
        self._emit_context: 'UnifiedEmitContext'

        self.function_factory = function_factory
        self.downstream_groups:Dict[int, Dict[int, 'Connection']] = {}
        self.downstream_group_roundrobin: Dict[int, int] = {}

    def runtime_init(self, ctx: 'RuntimeContext') -> None:
        try:
            self.name = ctx.name
            self.logger = CustomLogger(
                filename=f"Node_{ctx.name}",
                env_name=ctx.env_name,
                console_output="WARNING",
                file_output="DEBUG",
                global_output = "WARNING",
                name = f"{ctx.name}_{self.__class__.__name__}",
                session_folder=ctx.session_folder
            )
            self.runtime_context = ctx
            self.function = self.function_factory.create_function(self.name)

            self._emit_context = UnifiedEmitContext(name = ctx.name, session_folder=ctx.session_folder, env_name = ctx.env_name) 
            self.logger.debug(f"Created function instance with {self.function_factory}")

            self.function.runtime_init(ctx)
        except Exception as e:
            self.logger.error(f"Failed to create function instance: {e}", exc_info=True)

    def receive_packet(self, packet: 'Packet' = None):
        """
        Smart dispatch for multi-input operator.
        This method should be implemented by subclasses to handle incoming packets.
        """
        self.logger.debug(f"Received packet in operator {self.name}, index: {packet.input_index if packet else 'N/A'}")
        try:
            if packet is None or packet.payload is None:
                result = self.process()
                self.logger.debug(f"Operator {self.name} received empty packet, executed with result: {result}")
            else:
                result = self.process(packet.payload, packet.input_index)
                self.logger.debug(f"Operator {self.name} processed payload with result: {result}")
            if result is not None:
                self.emit(result)
        except Exception as e:
            self.logger.error(f"Error in {self.name}.receive_packet(): {e}", exc_info=True)


    @abstractmethod
    def process(self, raw_data:Any = None, input_index:int = 0) -> Any:
        """
        Process the raw data and return the result.
        This method should be implemented by subclasses to define the processing logic.
        
        Args:
            raw_data: The data to process, can be any type.
            input_index: The index of the input channel, default is 0.
        
        Returns:
            The processed result, can be any type.
        """
        pass

    def emit(self, raw_data: Any):

        """
        Emit data to downstream node through specified channel and target.
        现在直接将Connection对象传递给EmitContext处理
        
        Args:
            tag: The output tag, None for broadcast to all channels
            data: The data to emit
        """
        
        if self._emit_context is None:
            raise RuntimeError(f"Emit context not set for operator {self.name}. "
                            "This should be injected by the DAG node.")
    
        for broadcast_index, parallel_targets in self.downstream_groups.items():
            # round-robin选择
            current_round_robin = self.downstream_group_roundrobin[broadcast_index]
            connection = parallel_targets[current_round_robin % len(parallel_targets)]
            self.downstream_group_roundrobin[broadcast_index] += 1
            
            # 直接将Connection对象传递给EmitContext
            try:
                self._emit_context.send_via_connection(connection, raw_data)
                
            except Exception as e:
                self.logger.error(f"Failed to send data to target {connection.target_name} , group[{broadcast_index}]: {e}", exc_info=True)

    def add_connection(self, connection: 'Connection') -> None:
        """
        添加下游连接，使用Connection对象的属性作为索引，保存完整的Connection对象
        
        Args:
            connection: Connection对象，包含所有连接信息
        """
        broadcast_index = connection.broadcast_index
        parallel_index = connection.parallel_index
        
        # Debug log
        self.logger.debug(
            f"broadcast_index={broadcast_index}, parallel_index={parallel_index}, "
            f"target={connection.target_name}"
            f"connection_type={connection.connection_type.value}"
        )
        
        # 初始化广播组（如果不存在）
        if broadcast_index not in self.downstream_groups:
            self.downstream_groups[broadcast_index] = {}
            self.downstream_group_roundrobin[broadcast_index] = 0
        
        # 保存完整的Connection对象
        self.downstream_groups[broadcast_index][parallel_index] = connection
        
        # 打印连接的调试信息（可选）
        # if self.logger.isEnabledFor(10):  # DEBUG level
        # print(connection.debug_info())
        
        self.logger.debug(
            f"Added downstream connection: -> "
            f"{connection.target_name} "
            f"(type: {connection.connection_type.value})"
        )

    def get_downstream_connections(self, output_tag: str = None) -> List['Connection']:
        """
        获取所有下游连接，可选择性地按输出标签过滤
        
        Args:
            output_tag: 可选的输出标签过滤器
            
        Returns:
            List['Connection']: 连接列表
        """
        connections = []
        
        for broadcast_groups in self.downstream_groups.values():
            for connection in broadcast_groups.values():
                connections.append(connection)
        
        return connections
    
    def get_wrapped_operator(self):
        """
            这个方法是用来让ide满意的，用来代表OperatorWrapper提供的这个方法
        """
        pass