from abc import ABC, abstractmethod
from typing import Type, List, Tuple, Any, TYPE_CHECKING, Union
from sage.core.function.base_function import BaseFunction

from sage.utils.custom_logger import CustomLogger
from sage.runtime.communication.router.packet import Packet

if TYPE_CHECKING:
    from sage.runtime.runtime_context import RuntimeContext


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
