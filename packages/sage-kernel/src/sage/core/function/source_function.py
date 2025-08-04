from abc import ABC, abstractmethod
from typing import Type, List, Tuple, Any, TYPE_CHECKING, Union
from sage.core.function.base_function import BaseFunction

from sage.utils.logging.custom_logger import CustomLogger
if TYPE_CHECKING:
    from sage.runtime.task_context import TaskContext

class StopSignal:
    """
    停止信号类，用于标识任务停止
    """
    def __init__(self, name: str):
        self.name = name

    def __repr__(self) -> str:
        return f"<StopSignal {self.name}>"

class SourceFunction(BaseFunction):
    """
    源函数基类 - 数据生产者
    
    源函数不接收输入数据，只产生输出数据
    通常用于读取文件、数据库、API等外部数据源
    """

    @abstractmethod
    def execute(self) -> Any:
        """
        执行源函数逻辑，生产数据
        
        Returns:
            生产的数据
        """
        pass