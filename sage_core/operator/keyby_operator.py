from typing import List, Type, Union, Tuple, Dict, Set, TYPE_CHECKING, Any, Optional
from sage_core.operator.base_operator import BaseOperator
from sage_runtime.io.packet import Packet
if TYPE_CHECKING:
    from sage_runtime.io.connection import Connection

class KeyByOperator(BaseOperator):
    """
    KeyBy操作符，提取数据的分区键并应用自定义路由策略
    
    支持的分区策略：
    - hash: 基于键的哈希值分区
    - broadcast: 广播到所有下游实例
    - round_robin: 忽略键，轮询分发
    """
    
    def __init__(self,  *args, partition_strategy: str = "hash", **kwargs):
        super().__init__(*args, **kwargs)
        self.partition_strategy = partition_strategy
        self.logger.info(f"KeyByOperator '{self.name}' initialized with strategy: {partition_strategy}")

    def process(self, raw_data: Any, input_index: int = 0) -> Any:
        """
        提取键并创建带有分区信息的数据包
        
        Args:
            raw_data: 输入数据
            input_index: 输入索引
            
        Returns:
            dict: 包含键和数据的结构，用于下游路由
        """
        self.logger.debug(f"KeyByOperator '{self.name}' processing data: {raw_data}")
        
        try:
            # 使用function提取键
            extracted_key = self.function.execute(raw_data)
            
            # 创建带有分区信息的数据结构
            keyed_data = {
                'partition_key': extracted_key,
                'partition_strategy': self.partition_strategy,
                'original_data': raw_data
            }
            
            self.logger.debug(f"KeyByOperator '{self.name}' extracted key: {extracted_key}")
            return keyed_data
            
        except Exception as e:
            self.logger.error(f"Error in KeyByOperator '{self.name}'.process(): {e}", exc_info=True)
            # 返回原始数据，使用默认路由
            return raw_data

    def emit(self, keyed_data: Any):
        """
        重写emit方法以支持基于键的路由策略
        
        Args:
            keyed_data: 处理后的数据，可能包含分区信息
        """
        if self._emit_context is None:
            raise RuntimeError(f"Emit context not set for operator {self.name}")

        # 检查是否为KeyBy处理过的数据
        if isinstance(keyed_data, dict) and 'partition_key' in keyed_data:
            self._emit_keyed_data(keyed_data)
        else:
            # 回退到默认的round-robin行为
            super().emit(keyed_data)

    def _emit_keyed_data(self, keyed_data: Dict[str, Any]):
        partition_key = keyed_data['partition_key']
        strategy = keyed_data['partition_strategy']
        original_data = keyed_data['original_data']
        
        for broadcast_index, parallel_targets in self.downstream_groups.items():
            if strategy == "hash":
                target_index = hash(partition_key) % len(parallel_targets)
                connection = parallel_targets[target_index]
                # 创建带有分区信息的packet
                self._send_keyed_packet(connection, original_data, partition_key, strategy)
                
            elif strategy == "broadcast":
                # 广播到所有实例
                for connection in parallel_targets.values():
                    self._send_to_connection(connection, original_data)
                    
            elif strategy == "round_robin":
                # 忽略键，使用轮询（回退到父类行为）
                current_round_robin = self.downstream_group_roundrobin[broadcast_index]
                connection = parallel_targets[current_round_robin % len(parallel_targets)]
                self.downstream_group_roundrobin[broadcast_index] += 1
                self._send_to_connection(connection, original_data)
                
            else:
                self.logger.warning(f"Unknown partition strategy: {strategy}, using round-robin")
                # 回退到round-robin
                current_round_robin = self.downstream_group_roundrobin[broadcast_index]
                connection = parallel_targets[current_round_robin % len(parallel_targets)]
                self.downstream_group_roundrobin[broadcast_index] += 1
                self._send_to_connection(connection, original_data)

    def _send_keyed_packet(self, connection: 'Connection', data: Any, 
                        partition_key: Any, strategy: str):
        """发送带有分区信息的packet"""
        # 创建包含分区元数据的packet
        packet = Packet(
            payload=data,  # 纯净的业务数据
            input_index=connection.target_input_index,
            partition_key=partition_key,      # 分区键元数据
            partition_strategy=strategy       # 分区策略元数据
        )
        
        # 直接调用底层发送，绕过UnifiedEmitContext的再次封装
        self._emit_context.send_packet_direct(connection, packet)


