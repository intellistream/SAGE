from typing import Any, Callable, Union, Iterable, Optional

from sage_core.api.function_api.flatmap_function import FlatMapFunction
from sage_core.api.tuple import Data



class LambdaFlatMapFunction(FlatMapFunction):
    """
    基于Lambda表达式的FlatMap函数
    """
    
    def __init__(self, flat_map_func: Callable[[Any], Iterable[Any]], **kwargs):
        super().__init__(**kwargs)
        self.flat_map_func = flat_map_func
        self.logger.debug(f"LambdaFlatMapFunction initialized")

    def execute(self, data: Union[Any, Data]) -> Optional[Iterable[Any]]:
        """
        使用Lambda表达式进行FlatMap操作
        
        Args:
            data: 输入数据，可以是裸数据或Data封装
            
        Returns:
            Optional[Iterable[Any]]: 展开的数据列表
        """
        try:
            # 提取原始数据
            raw_data = self._extract_data(data)
            result = self.flat_map_func(raw_data)
            self.logger.debug(f"FlatMap result: {result} for data: {raw_data}")
            return result
        except Exception as e:
            self.logger.error(f"Error in flat_map_func for data {data}: {e}", exc_info=True)
            return None
