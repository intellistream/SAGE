from typing import Any, Callable, List

from sage_core.api.function_api.filter_function import FilterFunction
from sage_core.api.tuple import Data



class CompositeFilterFunction(FilterFunction):
    """
    组合过滤函数，支持多个条件的逻辑组合
    """
    
    def __init__(self, filters: List[FilterFunction], logic: str = "AND", **kwargs):
        super().__init__(**kwargs)
        self.filters = filters
        self.logic = logic.upper()
        if self.logic not in ["AND", "OR"]:
            raise ValueError("Logic must be 'AND' or 'OR'")
        self.logger.debug(f"CompositeFilterFunction initialized with {len(filters)} filters, logic: {logic}")

    def execute(self, data: Any) -> bool:
        """
        执行组合过滤条件
        
        Args:
            data: 输入数据
            
        Returns:
            bool: 过滤结果
        """
        try:
            if not self.filters:
                return True
            
            results = []
            for filter_func in self.filters:
                result = filter_func.execute(data)
                results.append(result)
            
            if self.logic == "AND":
                final_result = all(results)
            else:  # OR
                final_result = any(results)
            
            self.logger.debug(f"Composite filter ({self.logic}) result: {final_result} for data: {data}")
            return final_result
        except Exception as e:
            self.logger.error(f"Error in composite filter for data {data}: {e}", exc_info=True)
            return False