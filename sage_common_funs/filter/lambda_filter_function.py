from typing import Any, Callable, Union

from sage_core.api.function_api.filter_function import FilterFunction


class LambdaFilterFunction(FilterFunction):
    """
    基于Lambda表达式的Filter函数，方便快速创建过滤条件
    """
    
    def __init__(self, predicate: Callable[[Any], bool], **kwargs):
        super().__init__(**kwargs)
        self.predicate = predicate
        self.logger.debug(f"LambdaFilterFunction initialized with predicate: {predicate}")

    def execute(self, data) -> bool:
        """
        使用Lambda表达式判断数据是否通过过滤条件
        
        Args:
            data: 输入数据，可以是裸数据或Data封装
            
        Returns:
            bool: 过滤结果
        """
        try:
            # 提取原始数据
            result = self.predicate(data)
            self.logger.debug(f"Filter result: {result} for data: {data}")
            return self._process_output(result)
        except Exception as e:
            self.logger.error(f"Error in predicate for data {data}: {e}", exc_info=True)
            return False