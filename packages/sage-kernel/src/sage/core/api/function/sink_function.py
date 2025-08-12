from abc import ABC, abstractmethod
from typing import Type, List, Tuple, Any, TYPE_CHECKING, Union
from sage.core.api.function.base_function import BaseFunction


class SinkFunction(BaseFunction):
    """
    汇聚函数基类 - 数据消费者
    
    汇聚函数接收输入数据，通常不产生输出
    用于数据存储、发送、打印等终端操作
    """
    
    @abstractmethod
    def execute(self, data: Any) -> None:
        """
        执行汇聚操作
        
        Args:
            data: 输入数据
        """
        pass