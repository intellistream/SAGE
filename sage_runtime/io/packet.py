from typing import TypeVar, Generic, Any

T = TypeVar('T')
class Packet(Generic[T]):
    def __init__(self, payload: T, input_index: int = 0, 
                 partition_key: Any = None, partition_strategy: str = None):
        self.payload:Any = payload
        self.input_index:int = input_index
        self.partition_key = partition_key          # 新增：分区键
        self.partition_strategy = partition_strategy # 新增：分区策略