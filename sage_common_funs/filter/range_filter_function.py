from typing import Any, Callable, Optional, Union

from sage_core.api.function_api.filter_function import FilterFunction



class RangeFilterFunction(FilterFunction):
    """
    范围过滤函数，检查数值是否在指定范围内
    """
    
    def __init__(self, field_name: str, min_value: Optional[Union[int, float]] = None, 
                 max_value: Optional[Union[int, float]] = None, inclusive: bool = True, **kwargs):
        super().__init__(**kwargs)
        self.field_name = field_name
        self.min_value = min_value
        self.max_value = max_value
        self.inclusive = inclusive
        self.logger.debug(f"RangeFilterFunction initialized: field={field_name}, min={min_value}, max={max_value}")

    def execute(self, data: Any) -> bool:
        """
        检查指定字段的值是否在范围内
        
        Args:
            data: 输入数据
            
        Returns:
            bool: 过滤结果
        """
        try:
            if hasattr(data, self.field_name):
                value = getattr(data, self.field_name)
            elif hasattr(data, '__getitem__'):
                value = data[self.field_name]
            else:
                self.logger.warning(f"Cannot extract field '{self.field_name}' from data: {data}")
                return False
            
            # 检查范围
            if self.min_value is not None:
                if self.inclusive:
                    if value < self.min_value:
                        return False
                else:
                    if value <= self.min_value:
                        return False
            
            if self.max_value is not None:
                if self.inclusive:
                    if value > self.max_value:
                        return False
                else:
                    if value >= self.max_value:
                        return False
            
            self.logger.debug(f"Value {value} passed range filter")
            return True
        except Exception as e:
            self.logger.error(f"Error in range filter for data {data}: {e}", exc_info=True)
            return False
