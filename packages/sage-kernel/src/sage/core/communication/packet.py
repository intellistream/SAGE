"""
数据包 (Packet) - 算子间通信的基础数据结构

Packet 是流处理系统中算子间传递数据的标准载体，包含了数据负载、分区信息、时间戳等元数据。
这个类被设计为轻量级且不可变，以确保高效的数据传输。
"""

from typing import Any, Optional
import time


class Packet:
    """
    数据包类 - 算子间通信的基础数据结构
    
    Packet 封装了在流处理管道中传输的数据及其元数据。每个 Packet 包含：
    - payload: 实际的数据内容
    - input_index: 输入索引，用于多输入流场景
    - partition_key: 分区键，用于数据分区
    - partition_strategy: 分区策略
    - timestamp: 创建时间戳
    
    Attributes:
        payload: 数据负载，可以是任何类型的数据
        input_index: 输入流索引，默认为0
        partition_key: 分区键，用于确定数据分区
        partition_strategy: 分区策略（如 "hash", "range" 等）
        timestamp: 数据包创建时的纳秒级时间戳
    """
    
    def __init__(self, payload: Any, input_index: int = 0, 
                 partition_key: Any = None, partition_strategy: Optional[str] = None):
        """
        创建新的数据包
        
        Args:
            payload: 数据负载
            input_index: 输入流索引，用于区分多个输入流
            partition_key: 分区键，用于数据分区
            partition_strategy: 分区策略名称
        """
        self.payload = payload
        self.input_index = input_index
        self.partition_key = partition_key
        self.partition_strategy = partition_strategy
        self.timestamp = time.time_ns()
    
    def is_keyed(self) -> bool:
        """
        检查数据包是否包含分区键
        
        Returns:
            bool: 如果包含分区键则返回 True，否则返回 False
        """
        return self.partition_key is not None
    
    def inherit_partition_info(self, new_payload: Any) -> 'Packet':
        """
        创建新数据包，继承当前的分区信息
        
        这个方法常用于转换操作中，当需要保持数据的分区信息但更改负载内容时。
        
        Args:
            new_payload: 新的数据负载
            
        Returns:
            Packet: 包含新负载但继承分区信息的新数据包
        """
        return Packet(
            payload=new_payload,
            input_index=self.input_index,
            partition_key=self.partition_key,
            partition_strategy=self.partition_strategy,
        )
    
    def update_key(self, new_key: Any, new_strategy: Optional[str] = None) -> 'Packet':
        """
        更新分区键，用于重新分区场景
        
        这个方法用于需要改变数据分区的场景，例如 keyBy 操作。
        
        Args:
            new_key: 新的分区键
            new_strategy: 新的分区策略，如果为 None 则保持原策略
            
        Returns:
            Packet: 包含新分区信息的数据包
        """
        return Packet(
            payload=self.payload,
            input_index=self.input_index,
            partition_key=new_key,
            partition_strategy=new_strategy or self.partition_strategy,
        )
    
    def copy(self) -> 'Packet':
        """
        创建数据包的副本
        
        Returns:
            Packet: 数据包的完整副本
        """
        packet = Packet(
            payload=self.payload,
            input_index=self.input_index,
            partition_key=self.partition_key,
            partition_strategy=self.partition_strategy,
        )
        packet.timestamp = self.timestamp  # 保持原始时间戳
        return packet
    
    def __repr__(self) -> str:
        """
        返回数据包的字符串表示
        
        Returns:
            str: 数据包的描述信息
        """
        key_info = f"key={self.partition_key}" if self.is_keyed() else "unkeyed"
        payload_type = type(self.payload).__name__ if self.payload is not None else "None"
        
        return (f"<Packet input={self.input_index} {key_info} "
                f"payload_type={payload_type} ts={self.timestamp}>")
    
    def __eq__(self, other) -> bool:
        """
        比较两个数据包是否相等
        
        Args:
            other: 另一个数据包
            
        Returns:
            bool: 如果两个数据包相等则返回 True
        """
        if not isinstance(other, Packet):
            return False
        
        return (self.payload == other.payload and
                self.input_index == other.input_index and
                self.partition_key == other.partition_key and
                self.partition_strategy == other.partition_strategy)
