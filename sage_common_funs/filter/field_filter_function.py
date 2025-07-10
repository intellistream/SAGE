from typing import Any, Callable, Union

from sage_core.api.function_api.filter_function import FilterFunction
from sage_core.api.tuple import Data



class FieldFilterFunction(FilterFunction):
    """
    基于字段值的Filter函数，检查字段值是否满足条件
    """
    
    def __init__(self, field_name: str, condition: Callable[[Any], bool], **kwargs):
        super().__init__(**kwargs)
        self.field_name = field_name
        self.condition = condition
        self.logger.debug(f"FieldFilterFunction initialized with field_name: {field_name}")

    def execute(self, data: Union[Any, Data]) -> bool:
        """
        检查指定字段的值是否满足条件
        
        Args:
            data: 输入数据，可以是裸数据或Data封装
            
        Returns:
            bool: 过滤结果
        """
        try:
            # 提取原始数据
            raw_data = self._extract_data(data)
            
            if hasattr(raw_data, self.field_name):
                field_value = getattr(raw_data, self.field_name)
            elif hasattr(raw_data, '__getitem__'):
                field_value = raw_data[self.field_name]
            else:
                self.logger.warning(f"Cannot extract field '{self.field_name}' from data: {raw_data}")
                return False
            
            result = self.condition(field_value)
            self.logger.debug(f"Filter result: {result} for field '{self.field_name}' = {field_value}")
            return self._process_output(result)
        except Exception as e:
            self.logger.error(f"Error checking field '{self.field_name}' in data {data}: {e}", exc_info=True)
            return False