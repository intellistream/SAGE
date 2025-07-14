from typing import Any, Optional
from typing import Any, List, Dict, Optional, Set, TYPE_CHECKING, Type, Tuple
from sage_core.operator.base_operator import BaseOperator
from sage_core.function.filter_function import FilterFunction
from sage_runtime.io.packet import Packet

if TYPE_CHECKING:
    from sage_core.function.base_function import BaseFunction
    from sage_runtime.io.connection import Connection
    

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
        
        # # 验证函数类型
        # if not isinstance(self.function, FilterFunction):
        #     raise TypeError(f"{self.__class__.__name__} requires FilterFunction, got {type(self.function)}")
        
        # 统计信息
        self._total_input_count = 0
        self._passed_count = 0
        self._filtered_count = 0
        

    def process(self, data:Any, input_index: int = 0):
        """
        处理输入数据，根据过滤条件决定是否发送到下游
        
        Args:
            tag: 输入标签
            data: 输入数据
        """
        self.logger.debug(f"FilterOperator '{self.name}' received data': {data}")
        
        try:
            # 更新输入计数
            self._total_input_count += 1
            should_pass = self.function.execute(data)
            
            # 处理过滤结果
            if should_pass:
                self._passed_count += 1
                self.emit(data)
                self.logger.debug(f"FilterOperator '{self.name}' passed data: {data}")
            else:
                self._filtered_count += 1
                self.logger.debug(f"FilterOperator '{self.name}' filtered out data: {data}")
            
        except Exception as e:
            self.logger.error(f"Error in FilterOperator '{self.name}'.receive_packet(): {e}", exc_info=True)
            # 发生错误时，可以选择丢弃数据或者让数据通过
            # 这里选择丢弃数据，并增加过滤计数
            self._filtered_count += 1

    def get_filter_statistics(self) -> dict:
        """
        获取过滤统计信息
        
        Returns:
            dict: 包含过滤统计的字典
        """
        pass_rate = (self._passed_count / self._total_input_count * 100) if self._total_input_count > 0 else 0
        filter_rate = (self._filtered_count / self._total_input_count * 100) if self._total_input_count > 0 else 0
        
        return {
            "total_input": self._total_input_count,
            "passed": self._passed_count,
            "filtered": self._filtered_count,
            "pass_rate_percent": round(pass_rate, 2),
            "filter_rate_percent": round(filter_rate, 2)
        }

    def reset_statistics(self):
        """
        重置统计信息
        """
        self._total_input_count = 0
        self._passed_count = 0
        self._filtered_count = 0
        self.logger.debug(f"FilterOperator '{self.name}' statistics reset")

    def debug_print_filter_info(self):
        """
        打印过滤统计的调试信息
        """
        stats = self.get_filter_statistics()
        
        print(f"\n{'='*60}")
        print(f"🔍 FilterOperator '{self.name}' Statistics")
        print(f"{'='*60}")
        print(f"Total Input: {stats['total_input']}")
        print(f"Passed: {stats['passed']} ({stats['pass_rate_percent']}%)")
        print(f"Filtered: {stats['filtered']} ({stats['filter_rate_percent']}%)")
        print(f"{'='*60}\n")