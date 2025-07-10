from typing import Any, Callable, Optional

from sage_core.api.function_api.filter_function import FilterFunction
from sage_core.api.tuple import Data


class NotNullFilterFunction(FilterFunction):
    """
    非空过滤函数，过滤掉空值数据
    """
    
    def __init__(self, field_name: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.field_name = field_name
        self.logger.debug(f"NotNullFilterFunction initialized with field_name: {field_name}")

    def execute(self, data: Any) -> bool:
        """
        检查数据或指定字段是否为非空
        
        Args:
            data: 输入数据
            
        Returns:
            bool: 过滤结果
        """
        try:
            if self.field_name is None:
                # 检查整个数据对象
                result = data is not None
            else:
                # 检查指定字段
                if hasattr(data, self.field_name):
                    field_value = getattr(data, self.field_name)
                elif hasattr(data, '__getitem__'):
                    field_value = data[self.field_name]
                else:
                    return False
                
                result = field_value is not None and field_value != ""
            
            self.logger.debug(f"NotNull filter result: {result} for data: {data}")
            return result
        except Exception as e:
            self.logger.error(f"Error in NotNull filter for data {data}: {e}", exc_info=True)
            return False