from abc import abstractmethod
from typing import Any, List, Tuple, Type, Callable, Optional, Union
from sage.core.api.function.base_function import BaseFunction


class FilterFunction(BaseFunction):
    """
    FilterFunction 是专门用于 Filter 操作的函数基类。
    它定义了过滤条件函数的接口，用于判断数据是否应该通过过滤器。
    
    Filter 函数的主要作用是接收输入数据，返回布尔值表示数据是否通过过滤条件。
    
    Example usage:
        # 过滤正数
        class PositiveFilterFunction(FilterFunction):
            def execute(self, data):
                return data.value > 0
        
        # 过滤特定用户
        class UserFilterFunction(FilterFunction):
            def execute(self, data):
                return data.user_id in ['user1', 'user2']
        
        # 过滤空值
        class NotNullFilterFunction(FilterFunction):
            def execute(self, data):
                return data.value is not None and data.value != ""
    """


    @abstractmethod
    def execute(self, data: Any) -> bool:
        """
        抽象方法，由子类实现具体的过滤逻辑。
        
        Args:
            data: 输入数据，可以是裸数据或Data封装
            
        Returns:
            bool: True表示数据应该通过，False表示应该被过滤掉
        """
        pass

    def _process_output(self, result: Any) -> bool:
        """
        FilterFunction的输出处理，确保返回布尔值
        
        Args:
            result: 过滤函数的结果
            
        Returns:
            bool: 过滤结果
        """
        return bool(result)










