from typing import List, Type, Union, Tuple, Dict, Set, TYPE_CHECKING, Any, Optional
from sage.core.operator.base_operator import BaseOperator
from sage.core.communication.packet import Packet

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


    def process_packet(self, packet: 'Packet' = None):
        """重写packet处理，添加分区信息"""
        try:
            if packet is None or packet.payload is None:
                return
            
            # 提取分区键
            extracted_key = self.process(packet.payload)
            
            # 创建带有新分区信息的packet
            keyed_packet = packet.update_key(extracted_key, self.partition_strategy)
            
            self.logger.debug(f"KeyByOperator '{self.name}' added key '{extracted_key}' to packet")
            
            # 直接发送带有分区信息的packet
            self.router.send(keyed_packet)
            
        except Exception as e:
            self.logger.error(f"Error in KeyByOperator {self.name}: {e}", exc_info=True)
            # 回退：发送原始packet
            if packet:
                self.router.send(packet)


    def process(self, raw_data: Any, input_index: int = 0) -> Any:
        """提取键，返回原始数据（分区信息将在packet级别处理）"""
        try:
            extracted_key = self.function.execute(raw_data)
            self.logger.debug(f"KeyByOperator '{self.name}' extracted key: {extracted_key}")
            return extracted_key
            
        except Exception as e:
            self.logger.error(f"Error extracting key in {self.name}: {e}", exc_info=True)
            return raw_data
