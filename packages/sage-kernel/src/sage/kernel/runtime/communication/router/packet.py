from typing import TypeVar, Generic, Any, Optional
import time

class Packet:
    def __init__(self, payload: Any, input_index: int = 0, 
                 partition_key: Any = None, partition_strategy: str = None):
        self.payload = payload
        self.input_index = input_index
        self.partition_key = partition_key
        self.partition_strategy = partition_strategy
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
        )
    
    def update_key(self, new_key: Any, new_strategy: str = None) -> 'Packet':
        """更新分区键，用于重新分区场景"""
        return Packet(
            payload=self.payload,
            input_index=self.input_index,
            partition_key=new_key,
            partition_strategy=new_strategy or self.partition_strategy,
        )


class StopSignal:
    """停止信号类，用于通知流处理停止"""
    
    def __init__(self, message: str = "Stop", source: str = None):
        self.message = message
        self.source = source
        self.timestamp = time.time_ns()
    
    def __str__(self):
        return f"StopSignal({self.message})"
    
    def __repr__(self):
        return f"StopSignal(message='{self.message}', source='{self.source}')"