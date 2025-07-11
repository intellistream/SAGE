
from abc import ABC, abstractmethod
from typing import Any, List, Dict, Optional, Set, TYPE_CHECKING, Type, Tuple
from sage_utils.custom_logger import CustomLogger
from sage_runtime.io.unified_emit_context import UnifiedEmitContext
from sage_runtime.io.packet import Packet

if TYPE_CHECKING:
    from sage_core.api.base_function import BaseFunction
    from sage_runtime.io.connection import Connection
    from sage_runtime.operator.runtime_context import RuntimeContext




# TODO: 将Memory的API使用在这里。
# Operator 决定事件的逻辑路由（如广播、分区、keyBy等），
# EmitContext 仅负责将数据发送到指定的下游通道或节点。
# 路由策略是 Operator 的语义特征，EmitContext 专注于消息投递的物理实现。

class BaseOperator(ABC):
    def __init__(self, 
                 function_class: Type['BaseFunction'] = None,
                 function_args: Tuple = None,
                 function_kwargs: Dict[str, Any] = None,
                 session_folder: str = None, 
                 name: str = None, 
                 env_name:str = None, 
                 **kwargs):
        
        self.logger = CustomLogger(
            filename=f"Node_{name}",
            env_name=env_name,
            session_folder = session_folder or None,
            console_output="WARNING",
            file_output="DEBUG",
            global_output = "DEBUG",
            name = f"{name}_{self.__class__.__name__}"
        )
        self.name = name

        try:
            # TODO: 做一个函数工厂来处理函数的创建
            # Issue URL: https://github.com/intellistream/SAGE/issues/148
            # 新方式：传递function类和参数，在这里创建实例
            function_args = function_args or ()
            function_kwargs = function_kwargs or {}
            self.function = function_class(*function_args, **function_kwargs)
            self.logger.debug(f"Created function instance: {function_class.__name__} "
                            f"with args {function_args} and kwargs {function_kwargs}")
        except Exception as e:
            self.logger.error(f"Failed to create function instance: {e}", exc_info=True)

        self._emit_context = UnifiedEmitContext(name = name, session_folder=session_folder, env_name = env_name) 
    

 
        self.downstream_groups:Dict[int, Dict[int, 'Connection']] = {}
        self.downstream_group_roundrobin: Dict[int, int] = {}


        self.runtime_context = None

    

    def insert_emit_context(self, emit_context):
        """
        Inject the emit context into the operator.
        This is typically called by the DAG node to set up the context.
        
        Args:
            emit_context: The emit context to be injected
        """
        self._emit_context = emit_context
        self.logger.debug(f"Emit context injected for operator {self.name}")

    def insert_runtime_context(self, runtime_context  = None, env_name:str = None):
        self.runtime_context:'RuntimeContext' = runtime_context
        self.runtime_context.logger =CustomLogger(
            filename=f"Node_{self.runtime_context.name}",
            console_output="WARNING",
            file_output="DEBUG",
            global_output = "WARNING",
            session_folder=self.runtime_context.session_folder,
            name = f"{self.runtime_context.name}_RuntimeContext",
            env_name = env_name
        )
        

        self.function.insert_runtime_context(runtime_context)

    def receive_packet(self, packet: 'Packet' = None):
        """
        Smart dispatch for multi-input operator.
        """
        self.logger.debug(f"Received packet in operator {self.name}")
        try:
            if packet is None or packet.payload is None:
                result = self.function.execute()
                self.logger.debug(f"Operator {self.name} received empty packet, executed with result: {result}")
            else:
                result = self.function.execute(packet.payload)
                self.logger.debug(f"Operator {self.name} processed payload with result: {result}")
            if result is not None:
                self.emit(Packet(result))
        except Exception as e:
            self.logger.error(f"Error in {self.name}.receive_packet(): {e}", exc_info=True)


    def emit(self, result: Any):
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
                self._emit_context.send_via_connection(connection, result)
                
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