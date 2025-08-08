from typing import Any, Optional
from typing import Any, List, Dict, Optional, Set, TYPE_CHECKING, Type, Tuple
from sage.core.operator.base_operator import BaseOperator
from sage.core.communication.packet import Packet
    

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
                self.logger.debug(f"FilterOperator {self.name}: Received empty packet")
                return
            
            # 添加调试日志
            self.logger.info(f"FilterOperator {self.name}: Processing packet with payload: {packet.payload}")
            
            # 执行过滤逻辑
            should_pass = self.function.execute(packet.payload)
            
            self.logger.info(f"FilterOperator {self.name}: Filter result: {should_pass}")
            
            if should_pass:
                # 通过过滤，继承分区信息
                self.logger.info(f"FilterOperator {self.name}: Sending packet downstream")
                self.router.send(packet)
            else:
                self.logger.info(f"FilterOperator {self.name}: Packet filtered out")
            # 不通过过滤：不发送任何packet
            
        except Exception as e:
            self.logger.error(f"Error in FilterOperator {self.name}: {e}", exc_info=True)