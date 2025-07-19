
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

class BaseOperator(ABC):
    def __init__(self, 
                 function_factory: 'FunctionFactory', ctx: 'RuntimeContext', *args,
                 **kwargs):
        
        self.name:str
        self.function:'BaseFunction'
        self._emit_context: 'UnifiedEmitContext'

        self.function_factory = function_factory
        self.downstream_groups:Dict[int, Dict[int, 'Connection']] = {}
        self.downstream_group_roundrobin: Dict[int, int] = {}

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
            self.function = self.function_factory.create_function(self.name, ctx)

            self._emit_context = UnifiedEmitContext(name = ctx.name, session_folder=ctx.session_folder, env_name = ctx.env_name) 
            self.logger.debug(f"Created function instance with {self.function_factory}")

        except Exception as e:
            self.logger.error(f"Failed to create function instance: {e}", exc_info=True)

    def receive_packet(self, packet: 'Packet' = None):
        self.process_packet(packet)
        from sage_core.function.base_function import StatefulFunction
        if isinstance(self.function, StatefulFunction):
            self.function.save_state()

    @abstractmethod
    def process_packet(self, packet: 'Packet' = None):
        return


    def emit_packet(self, packet: 'Packet'):
        """
        新增：直接发送packet，根据其分区信息选择路由策略
        
        Args:
            packet: 要发送的packet，可能包含分区信息
        """
        if self._emit_context is None:
            raise RuntimeError(f"Emit context not set for operator {self.name}")
        self.logger.debug(f"Emitting packet: {packet}")
        # 根据packet的分区信息选择路由策略
        if packet.is_keyed():
            self._emit_keyed_packet(packet)
        else:
            self._emit_round_robin_packet(packet)

    def _emit_keyed_packet(self, packet: 'Packet'):
        """使用分区信息进行路由"""
        strategy = packet.partition_strategy
        partition_key = packet.partition_key
        
        for broadcast_index, parallel_targets in self.downstream_groups.items():
            if strategy == "hash":
                target_index = hash(partition_key) % len(parallel_targets)
                connection = parallel_targets[target_index]
                self._send_packet_to_connection(connection, packet)
                
            elif strategy == "broadcast":
                # 广播到所有实例
                for connection in parallel_targets.values():
                    self._send_packet_to_connection(connection, packet)
                    
            elif strategy == "round_robin":
                # 忽略键，使用轮询
                current_round_robin = self.downstream_group_roundrobin[broadcast_index]
                connection = parallel_targets[current_round_robin % len(parallel_targets)]
                self.downstream_group_roundrobin[broadcast_index] += 1
                self._send_packet_to_connection(connection, packet)
                
            else:
                self.logger.warning(f"Unknown partition strategy: {strategy}, using round-robin")
                self._emit_round_robin_packet(packet)

    def _emit_round_robin_packet(self, packet: 'Packet'):
        """使用round-robin策略路由"""
        for broadcast_index, parallel_targets in self.downstream_groups.items():
            current_round_robin = self.downstream_group_roundrobin[broadcast_index]
            connection = parallel_targets[current_round_robin % len(parallel_targets)]
            self.downstream_group_roundrobin[broadcast_index] += 1
            self._send_packet_to_connection(connection, packet)

    def _send_packet_to_connection(self, connection: 'Connection', packet: 'Packet'):
        """发送packet到指定连接"""
        try:
            # 更新packet的目标输入索引
            routed_packet = Packet(
                payload=packet.payload,
                input_index=connection.target_input_index,
                partition_key=packet.partition_key,
                partition_strategy=packet.partition_strategy,
            )
            
            self._emit_context.send_packet_direct(connection, routed_packet)
            self.logger.debug(f"Sent {'keyed' if packet.is_keyed() else 'unkeyed'} packet to {connection.target_name}")
            
        except Exception as e:
            self.logger.error(f"Failed to send packet to {connection.target_name}: {e}", exc_info=True)



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
    
    def get_wrapped_object(self):
        """
            这个方法是用来让ide满意的，用来代表OperatorWrapper提供的这个方法
        """
        pass

    def _send_to_connection(self, connection:'Connection', data):
        """
        发送数据到指定连接的辅助方法
        
        Args:
            connection: 目标连接
            data: 要发送的数据（已解包的原始数据）
        """
        try:
            packet = Packet(data, connection.target_input_index)
            self._emit_context.send_packet_direct(connection, packet)
            self.logger.debug(f"Sent data to {connection.target_name}")
        except Exception as e:
            self.logger.error(f"Failed to send data to {connection.target_name}: {e}", exc_info=True)