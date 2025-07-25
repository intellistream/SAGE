from typing import Any, Optional
from typing import Any, List, Dict, Optional, Set, TYPE_CHECKING, Type, Tuple
from sage.core.operator.base_operator import BaseOperator
from sage.core.function.filter_function import FilterFunction
from sage.runtime.router.packet import Packet

if TYPE_CHECKING:
    from sage.core.function.base_function import BaseFunction
    from sage.runtime.router.connection import Connection
    

class FilterOperator(BaseOperator):
    """
    Filter操作符，根据指定的条件函数对数据进行筛选。
    
    只有满足条件的数据才会被发送到下游节点。
    Filter操作不修改数据内容，只是决定数据是否通过。
    
    Example:
        # 过滤正数
        def filter_positive(data):
            return data.value > 0
        
        # 过滤特定用户
        def filter_user(data):
            return data.user_id in ['user1', 'user2']
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
    def process_packet(self, packet: 'Packet' = None):
        """Filter需要特殊处理：可能不产生输出"""
        try:
            if packet is None or packet.payload is None:
                return
            
            # 执行过滤逻辑
            should_pass = self.function.execute(packet.payload)
            
            if should_pass:
                # 通过过滤，继承分区信息
                self.router.send(packet)
            # 不通过过滤：不发送任何packet
            
        except Exception as e:
            self.logger.error(f"Error in FilterOperator {self.name}: {e}", exc_info=True)