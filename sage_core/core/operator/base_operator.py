
from abc import ABC, abstractmethod
from typing import Any, List, Dict, Optional, Set, TYPE_CHECKING
from sage_core.api.collector import Collector
from sage_utils.custom_logger import CustomLogger
from sage_runtime.io.unified_emit_context import UnifiedEmitContext


if TYPE_CHECKING:
    from sage_core.api.base_function import BaseFunction
    from sage_runtime.io.connection import Connection
    from sage_core.api.tuple import Data




# TODO: 将Memory的API使用在这里。
# Operator 决定事件的逻辑路由（如广播、分区、keyBy等），
# EmitContext 仅负责将数据发送到指定的下游通道或节点。
# 路由策略是 Operator 的语义特征，EmitContext 专注于消息投递的物理实现。

class BaseOperator(ABC):
    def __init__(self, function: 'BaseFunction', session_folder: Optional[str] = None, name: Optional[str] = None):
        self.collector = Collector(self)  # 用于收集数据
        self.logger = CustomLogger(
            filename=f"Node_{name}",
            session_folder = session_folder or None,
            console_output="WARNING",
            file_output="WARNING",
            global_output = "WARNING",
            name = f"{name}_{self.__class__.__name__}"
        )
        self.function = function
        self._emit_context = UnifiedEmitContext(name = name, session_folder=session_folder)

        self.function.insert_collector(self.collector)

        self._name = self.__class__.__name__
        # 维护下游节点和路由逻辑
        # downstream_channel->broadcasting_groups->targets
        self.downstream_channels:Dict[str, Dict[int, Dict[int, 'Connection']]] = {}
        # self.downstream_channels: Dict[int,Dict[int, List[DownstreamTarget]] ] = {}
        self.downstream_round_robin: Dict[str, Dict[int, int]] = {}
        for index, (output_tag, output_type) in enumerate(self.function.declare_outputs()):
            self.downstream_channels[output_tag] = {}
            self.downstream_round_robin[output_tag] = {}


        self.runtime_context = None

    

    def insert_emit_context(self, emit_context):
        """
        Inject the emit context into the operator.
        This is typically called by the DAG node to set up the context.
        
        Args:
            emit_context: The emit context to be injected
        """
        self._emit_context = emit_context
        self.logger.debug(f"Emit context injected for operator {self._name}")

    def insert_runtime_context(self, runtime_context  = None):
        self.runtime_context = runtime_context
        self.function.insert_runtime_context(runtime_context)

    def process_data(self, tag: str, data: 'Data'):
        """
        Smart dispatch for multi-input operator.
        """
        try:
            if(len(self.function.__class__.declare_inputs()) == 0):
                # No inputs declared, call execute without arguments
                result = self.function.execute()
            elif(len(self.function.__class__.declare_inputs()) == 1):
                result = self.function.execute(data)
            else:
                result = self.function.execute(tag, data)
            if result is not None:
                self.emit(None, result)

        except Exception as e:
            self.logger.error(f"Error in {self._name}.process_data(): {e}")
            raise


    def emit(self, tag: str, data: Any):
        """
        Emit data to downstream node through specified channel and target.
        现在直接将Connection对象传递给EmitContext处理
        
        Args:
            tag: The output tag, None for broadcast to all channels
            data: The data to emit
        """
        if self._emit_context is None:
            raise RuntimeError(f"Emit context not set for operator {self._name}. "
                            "This should be injected by the DAG node.")
        
        # 确定要发送的通道列表
        if tag is None:
            # x轴广播到所有下游通道
            target_groups = self.downstream_channels.items()
        else:
            if tag not in self.downstream_channels:
                self.logger.warning(f"Invalid output tag '{tag}' for operator {self._name}.")
                return
            target_groups = [(tag, self.downstream_channels[tag])]

        # 向每个通道发送数据
        for output_tag, broadcast_groups in target_groups:
            for broadcast_index, parallel_targets in broadcast_groups.items():
                # round-robin选择
                current_round_robin = self.downstream_round_robin[output_tag][broadcast_index]
                connection = parallel_targets[current_round_robin % len(parallel_targets)]
                self.downstream_round_robin[output_tag][broadcast_index] += 1
                
                # 直接将Connection对象传递给EmitContext
                try:
                    self._emit_context.send_via_connection(connection, data)
                    
                except Exception as e:
                    self.logger.error(f"Failed to send data to target {connection.target_name} "
                                    f"on tag {output_tag} group[{broadcast_index}]: {e}", exc_info=True)

    def add_connection(self, connection: 'Connection') -> None:
        """
        添加下游连接，使用Connection对象的属性作为索引，保存完整的Connection对象
        
        Args:
            connection: Connection对象，包含所有连接信息
        """
        # 从Connection对象中提取索引信息
        output_tag = connection.output_tag
        broadcast_index = connection.broadcast_index
        parallel_index = connection.parallel_index
        
        # Debug log
        self.logger.debug(
            f"Adding downstream connection: output_tag={output_tag}, "
            f"broadcast_index={broadcast_index}, parallel_index={parallel_index}, "
            f"target={connection.target_name}, target_input_tag={connection.target_input_tag}, "
            f"connection_type={connection.connection_type.value}"
        )

        # 验证输出标签是否存在
        if output_tag not in self.downstream_channels:
            raise ValueError(f"Output tag '{output_tag}' not found in operator {self._name}. "
                            "Ensure the output tag is declared in the function.")
        
        # 初始化广播组（如果不存在）
        if broadcast_index not in self.downstream_channels[output_tag]:
            self.downstream_channels[output_tag][broadcast_index] = {}
            self.downstream_round_robin[output_tag][broadcast_index] = 0
        
        # 保存完整的Connection对象
        self.downstream_channels[output_tag][broadcast_index][parallel_index] = connection
        
        # 打印连接的调试信息（可选）
        # if self.logger.isEnabledFor(10):  # DEBUG level
        connection.print_debug_info()
        
        self.logger.debug(
            f"Added downstream connection: [out:{output_tag}] -> "
            f"{connection.target_name}[in:{connection.target_input_tag}] "
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
        
        if output_tag is not None:
            # 返回特定输出标签的连接
            if output_tag in self.downstream_channels:
                for broadcast_groups in self.downstream_channels[output_tag].values():
                    for connection in broadcast_groups.values():
                        connections.append(connection)
        else:
            # 返回所有连接
            for tag_connections in self.downstream_channels.values():
                for broadcast_groups in tag_connections.values():
                    for connection in broadcast_groups.values():
                        connections.append(connection)
        
        return connections

    def debug_print_connections(self):
        """
        打印所有连接的调试信息
        """
        print(f"\n{'='*80}")
        print(f"🔗 Operator '{self._name}' Downstream Connections")
        print(f"{'='*80}")
        
        total_connections = 0
        for output_tag, broadcast_groups in self.downstream_channels.items():
            print(f"\n📤 Output Tag: '{output_tag}'")
            
            for broadcast_index, parallel_targets in broadcast_groups.items():
                print(f"  📊 Broadcast Group {broadcast_index}:")
                
                for parallel_index, connection in parallel_targets.items():
                    print(f"    🔢 Parallel #{parallel_index}: {connection.get_summary()}")
                    total_connections += 1
        
        print(f"\n📈 Total Connections: {total_connections}")
        print(f"{'='*80}\n")

    def get_connection_summary(self) -> Dict[str, Any]:
        """
        获取连接的统计摘要
        
        Returns:
            Dict: 包含连接统计信息的字典
        """
        summary = {
            "operator_name": self._name,
            "output_tags": list(self.downstream_channels.keys()),
            "total_connections": 0,
            "connections_by_type": {},
            "connections_by_tag": {}
        }
        
        for output_tag, broadcast_groups in self.downstream_channels.items():
            tag_count = 0
            for broadcast_groups_dict in broadcast_groups.values():
                for connection in broadcast_groups_dict.values():
                    # 统计总数
                    summary["total_connections"] += 1
                    tag_count += 1
                    
                    # 按类型统计
                    conn_type = connection.connection_type.value
                    if conn_type not in summary["connections_by_type"]:
                        summary["connections_by_type"][conn_type] = 0
                    summary["connections_by_type"][conn_type] += 1
            
            # 按标签统计
            summary["connections_by_tag"][output_tag] = tag_count
        
        return summary