from typing import TypeVar, Generic, Any, Optional
import time

class Packet:
    def __init__(self, payload: Any, input_index: int = 0, 
                 partition_key: Any = None, partition_strategy: str = None,
                 source_stream_index: Optional[int] = None):
        self.payload = payload
        self.input_index = input_index
        self.partition_key = partition_key
        self.partition_strategy = partition_strategy
        self.source_stream_index = source_stream_index
        self.timestamp = time.time_ns()
    
    def is_keyed(self) -> bool:
        """检查packet是否包含分区信息"""
        return self.partition_key is not None
    
    def inherit_partition_info(self, new_payload: Any) -> 'Packet':
        """创建新packet，继承当前的分区信息"""
        return Packet(
            payload=new_payload,
            input_index=self.input_index,
            partition_key=self.partition_key,
            partition_strategy=self.partition_strategy,
            source_stream_index=self.source_stream_index
        )
    
    def update_key(self, new_key: Any, new_strategy: str = None) -> 'Packet':
        """更新分区键，用于重新分区场景"""
        return Packet(
            payload=self.payload,
            input_index=self.input_index,
            partition_key=new_key,
            partition_strategy=new_strategy or self.partition_strategy,
            source_stream_index=self.source_stream_index
        )