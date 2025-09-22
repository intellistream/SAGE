from abc import ABC, abstractmethod
from typing import Type, List, Tuple, Any, TYPE_CHECKING, Union
from sage.core.api.function.base_function import BaseFunction


class MapFunction(BaseFunction):
    """
    映射函数基类 - 一对一数据变换
    
    映射函数接收一个输入，产生一个输出
    用于数据转换、增强、格式化等操作
    """

    @abstractmethod
    def execute(self, data: Any) -> Any:
        """
        执行映射变换
        
        Args:
            data: 输入数据
            
        Returns:
            变换后的数据
        """
        pass
